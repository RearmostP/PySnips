"""A temporary ONEFILE updater coordinates Setup while installed files are unlocked."""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from core.common.paths import PROJECT_ROOT
from core.common.version import version_parts
from core.updater.updater import UpdateError, _file_sha256, INSTALLER_NAME

PROCESS_WAIT_SECONDS = 60
INSTALL_WAIT_SECONDS = 15 * 60
STALE_SECONDS = 7 * 24 * 60 * 60


def session_root():
    return Path(tempfile.gettempdir()) / 'PySnips'


def create_session():
    root = session_root()
    root.mkdir(parents=True, exist_ok=True)
    session = Path(tempfile.mkdtemp(prefix='update-session-', dir=root))
    (session / 'owner.pid').write_text(str(os.getpid()), encoding='ascii')
    return session


def _windows_process(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE, never terminate.
    if not handle and ctypes.get_last_error() != 87:  # ERROR_INVALID_PARAMETER: exited PID.
        raise OSError(ctypes.get_last_error(), 'Unable to observe process')
    return kernel, handle


def process_alive(pid):
    if pid <= 0:
        return False
    if sys.platform == 'win32':
        kernel, handle = _windows_process(pid)
        if not handle:
            return False
        try:
            result = kernel.WaitForSingleObject(handle, 0)
            if result not in (0, 258):
                raise OSError('Unable to observe process exit status')
            return result == 258
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def wait_for_process(pid, timeout=PROCESS_WAIT_SECONDS, *, alive=process_alive, clock=time.monotonic, pause=time.sleep):
    if pid <= 0 or pid == os.getpid():
        raise UpdateError('Invalid process to wait for')
    deadline = clock() + timeout
    while alive(pid):
        if clock() >= deadline:
            raise UpdateError('Timed out waiting for PySnips or the original updater to close')
        pause(0.1)  # Runs exclusively in the apply worker, never the GUI thread.


def cleanup_stale(current=None, *, now=None):
    """Conservative best effort; never follow links or remove a live/current session."""
    now = time.time() if now is None else now
    root = session_root()
    try:
        for path in root.glob('update-session-*'):
            if path.is_symlink() or not path.is_dir() or path.resolve() == Path(current or sys.executable).resolve().parent:
                continue
            if current and path.resolve() == Path(current).resolve():
                continue
            try:
                if now - path.stat().st_mtime < STALE_SECONDS:
                    continue
                owners = list(path.glob('*.pid'))
                if any(process_alive(int(owner.read_text(encoding='ascii'))) for owner in owners):
                    continue
                shutil.rmtree(path)
            except (OSError, ValueError):
                continue
        # Old backend downloads may have left partial files; recent ones may be active.
        for path in (root / 'updates').glob('*.part'):
            if not path.is_symlink() and now - path.stat().st_mtime >= STALE_SECONDS:
                try:
                    path.unlink()
                except OSError:
                    pass
    except OSError:
        pass


def external_environment():
    environment = os.environ.copy()
    environment['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    for name in ('QT_PLUGIN_PATH', 'QML2_IMPORT_PATH'):
        environment.pop(name, None)
    return environment


@contextmanager
def system_dll_search():
    # PyInstaller changes Windows DLL search globally; Setup must use system DLLs.
    frozen = getattr(sys, 'frozen', False)
    if sys.platform == 'win32' and frozen:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.SetDllDirectoryW.argtypes = [wintypes.LPCWSTR]
        kernel.SetDllDirectoryW(None)
    try:
        yield
    finally:
        if sys.platform == 'win32' and frozen:
            kernel.SetDllDirectoryW(str(sys._MEIPASS))


def temporary_command(session, installer, version, checksum, app_path, app_pid, language,
                      *, frozen=None, executable=None, updater_pid=None):
    frozen = getattr(sys, 'frozen', False) if frozen is None else frozen
    executable = Path(executable or sys.executable).resolve()
    if frozen:
        copied = Path(session) / 'PySnipsUpdater.exe'
        shutil.copy2(executable, copied)
        command = [str(copied)]
    else:
        # Copying python.exe would not copy the updater or its dependencies.
        command = [str(executable), '-m', 'core.updater']
    return command + [
        '--apply-update', '--session', str(session), '--installer', str(installer),
        '--target-version', version, '--checksum', checksum, '--app-path', str(app_path),
        '--app-pid', str(app_pid), '--updater-pid', str(updater_pid or (os.getppid() if frozen else os.getpid())),
        '--language', language,
    ]


def launch_temporary(session, installer, version, checksum, app_path, app_pid, language):
    if _file_sha256(Path(installer)) != checksum:
        raise UpdateError('Installer SHA-256 checksum mismatch')
    command = temporary_command(session, installer, version, checksum, app_path, app_pid, language)
    ready = Path(session) / 'coordinator.ready'
    ready.unlink(missing_ok=True)
    try:
        with system_dll_search():
            working_directory = session if getattr(sys, 'frozen', False) else PROJECT_ROOT
            child = subprocess.Popen(command, cwd=str(working_directory), env=external_environment())
        deadline = time.monotonic() + 20
        while not ready.is_file():
            if child.poll() is not None or time.monotonic() >= deadline:
                # A late-starting child must not apply after a failed handoff.
                (Path(session) / 'handoff.cancelled').touch()
                raise UpdateError('Unable to start the temporary updater')
            time.sleep(0.05)
    except OSError as error:
        raise UpdateError('Unable to start the temporary updater') from error


def installer_command(installer, install_directory):
    return [str(installer), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/SP-', '/NORESTART',
            '/RESTARTEXITCODE=3010', '/NOCLOSEAPPLICATIONS', '/NORESTARTAPPLICATIONS',
            '/DIR=' + str(install_directory), '/LOG']


def run_installer(command, *, timeout, env, check=False):
    process = subprocess.Popen(command, env=env)
    # wait(timeout) leaves Setup alive if it takes too long: never kill an installer mid-write.
    return subprocess.CompletedProcess(command, process.wait(timeout=timeout))


def apply_update(args, status, *, wait=wait_for_process, run=run_installer, launch=subprocess.Popen):
    try:
        version_parts(args.target_version)
        session = Path(args.session).resolve()
        installer = Path(args.installer).resolve()
        app_path = Path(args.app_path).resolve()
        if installer.parent != session or installer.name != INSTALLER_NAME.format(version=args.target_version):
            raise UpdateError('Invalid update session installer')
        if not installer.is_file() or installer.suffix.lower() != '.exe':
            raise UpdateError('Installer must be an existing .exe file')
        if _file_sha256(installer) != args.checksum:
            raise UpdateError('Installer SHA-256 checksum mismatch')
        (session / 'coordinator.pid').write_text(str(os.getpid()), encoding='ascii')
        (session / 'coordinator.ready').touch()
        status('updater.waiting')
        wait(args.updater_pid)
        if args.app_pid:
            wait(args.app_pid)
        if (session / 'handoff.cancelled').exists():
            raise UpdateError('Update handoff was cancelled')
        # Source handoffs can exercise the coordinator, but never overwrite a source tree.
        if app_path.suffix.lower() != '.exe':
            raise UpdateError('Source mode cannot install an update; use a packaged PySnips installation')
        if not app_path.is_file() or app_path.name.lower() != 'pysnips.exe':
            raise UpdateError('Installed PySnips executable was not found')
        # Recheck after waiting: never execute a changed download.
        if _file_sha256(installer) != args.checksum:
            raise UpdateError('Installer SHA-256 checksum mismatch')
        status('updater.installing')
        with system_dll_search():
            result = run(installer_command(installer, app_path.parent),
                         timeout=INSTALL_WAIT_SECONDS, env=external_environment(), check=False)
        if result.returncode != 0:
            raise UpdateError(f'Installer failed (exit code {result.returncode})')
        status('updater.restarting')
        with system_dll_search():
            launch([str(app_path)], cwd=str(app_path.parent), env=external_environment())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise UpdateError(str(error)) from error
