from argparse import Namespace
from io import BytesIO
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from core.common.paths import PROJECT_ROOT
from core.common.update_process import RESTART_UPDATE_EXIT_CODE, UpdaterProcess, updater_command
from core.common.version import read_version, VersionError
from core.localization.localization import Localization
from core.settings.settings import Settings
from core.snips.library import SnippetLibrary
from core.theme.theme_manager import ThemeManager
from core.ui.main_window import MainWindow
from core.updater import UpdateError, UpdateInfo, Updater
from core.updater.app import UpdaterWindow, UpdateWorker, parser, remaining_download_ms
from core.updater.handoff import (apply_update, cleanup_stale, create_session, installer_command, run_installer,
                                  launch_temporary, temporary_command, wait_for_process)
from core.updater.updater import CHUNK_SIZE, _download_installer


class ProgressTests(unittest.TestCase):
    def test_real_byte_progress_and_missing_length(self):
        payload = b'a' * CHUNK_SIZE + b'last'
        for length in (str(len(payload)), None, 'invalid', '0'):
            with self.subTest(length=length), tempfile.TemporaryDirectory() as directory:
                response = BytesIO(payload)
                response.headers = {} if length is None else {'Content-Length': length}
                progress = []
                with patch('core.updater.updater.urlopen', return_value=response):
                    path = Path(directory) / 'download.part'
                    _download_installer('https://example.com/file', path, lambda *value: progress.append(value))
                total = len(payload) if length == str(len(payload)) else None
                self.assertEqual(progress, [(0, total), (CHUNK_SIZE, total), (len(payload), total)])
                self.assertEqual(path.read_bytes(), payload)

    def test_truncated_content_length_cleans_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            response = BytesIO(b'partial')
            response.headers = {'Content-Length': '100'}
            with patch('core.updater.updater.urlopen', return_value=response), self.assertRaises(UpdateError):
                Updater().download(UpdateInfo('0.2.1', 'https://example.com/exe', 'https://example.com/hash', ''), directory=directory)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_minimum_uses_elapsed_real_time_without_sleep(self):
        for started, now, expected in ((10, 10, 2000), (10, 10.5, 1500), (10, 12, 0), (10, 15, 0)):
            self.assertEqual(remaining_download_ms(started, now), expected)


class QtUpdaterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def window(self, mode='--check', language='en'):
        window = UpdaterWindow(parser().parse_args([mode, '--language', language]), updater=MagicMock(), clock=lambda: 10.5)
        self.addCleanup(window.deleteLater)
        return window

    def complete(self, window, stage, result=None, error=None):
        window.stage = stage
        window.worker = MagicMock(result=result, error=error)
        with patch('core.updater.app.QApplication.exit') as exited:
            window.completed()
        return exited

    def test_silent_no_update_and_error_never_show_ui(self):
        for result, error in ((('0.2.0', None), None), (None, UpdateError('offline'))):
            window = self.window('--check-silent')
            exited = self.complete(window, 'check', result, error)
            exited.assert_called_once_with(0)
            self.assertFalse(window.isVisible())

    def test_silent_update_opens_ui_without_downloading(self):
        window = self.window('--check-silent')
        update = UpdateInfo('0.2.1', 'https://example.com/exe', 'https://example.com/hash', 'Release notes')
        exited = self.complete(window, 'check', ('0.2.0', update))
        exited.assert_not_called()
        self.assertTrue(window.isVisible())
        self.assertEqual(window.notes.toPlainText(), 'Release notes')
        self.assertEqual(window.primary.text(), window.text('updater.download_install').replace('&', '&&'))
        window.updater.download.assert_not_called()

    def test_manual_no_update_is_visible_with_version(self):
        window = self.window()
        exited = self.complete(window, 'check', ('0.2.0', None))
        exited.assert_not_called()
        self.assertTrue(window.isVisible())
        self.assertEqual(window.heading.text(), window.text('updater.up_to_date'))
        self.assertIn('0.2.0', window.details.text())

    def test_manual_error_visible_and_download_error_never_requests_restart(self):
        for mode, stage in (('--check', 'check'), ('--check-silent', 'download'), ('--check', 'handoff'), ('--apply-update', 'apply')):
            window = self.window(mode)
            exited = self.complete(window, stage, error=UpdateError('offline'))
            exited.assert_not_called()
            self.assertTrue(window.isVisible())
            self.assertEqual(window.heading.text(), window.text('updater.failed'))
            self.assertEqual(window.exit_code, 1)

    def test_progress_determinate_and_indeterminate(self):
        window = self.window()
        window.report_progress(3 * 1048576, 4 * 1048576)
        self.assertEqual(window.progress.value(), 75)
        self.assertEqual(window.bytes.text(), '3.0 MB / 4.0 MB')
        window.report_progress(1048576, None)
        self.assertEqual((window.progress.minimum(), window.progress.maximum()), (0, 0))
        self.assertEqual(window.bytes.text(), '1.0 MB')

    def test_fast_download_waits_only_for_ready_transition(self):
        window = self.window()
        window.download_started = 10
        with patch.object(window.ready_timer, 'start') as timer:
            self.complete(window, 'download', (Path('setup.exe'), 'a' * 64))
        timer.assert_called_once_with(1500)
        self.assertTrue(window.busy)
        window.clock = lambda: 12
        window.show_ready()
        self.assertFalse(window.busy)
        self.assertEqual(window.stage, 'ready')
        self.assertEqual(window.primary.text(), window.text('updater.restart_update').replace('&', '&&'))

    def test_early_timer_wakeup_cannot_shorten_minimum(self):
        window = self.window()
        window.download_started = 9
        window.stage = 'download'
        with patch.object(window.ready_timer, 'start') as timer:
            window.show_ready()
        timer.assert_called_once_with(500)
        self.assertEqual(window.stage, 'download')

    def test_source_restart_does_not_close_application(self):
        window = self.window()
        window.show_ready()
        with patch('core.updater.app.QApplication.exit') as exited, patch.object(window, 'start_worker') as worker:
            window.primary_action()
        exited.assert_not_called()
        worker.assert_not_called()
        self.assertEqual(window.stage, 'error')

    def test_close_ready_does_not_install_or_request_restart(self):
        window = self.window()
        window.show_ready()
        with patch('core.updater.app.QApplication.exit') as exited, patch('core.updater.app.launch_temporary') as launch:
            window.close()
        exited.assert_called_once_with(0)
        launch.assert_not_called()

    def test_restart_exit_only_after_successful_handoff(self):
        window = self.window()
        exited = self.complete(window, 'handoff')
        exited.assert_called_once_with(RESTART_UPDATE_EXIT_CODE)

    def test_check_runs_in_worker_and_manual_shows_checking(self):
        for mode, visible in (('--check', True), ('--check-silent', False)):
            window = self.window(mode)
            with patch.object(window, 'start_worker') as start:
                window.start()
            self.assertEqual(window.isVisible(), visible)
            self.assertEqual(window.heading.text(), window.text('updater.checking'))
            window.updater.current_version = '0.2.0'
            window.updater.check.return_value = None
            self.assertEqual(start.call_args.args[1](MagicMock()), ('0.2.0', None))

    def test_worker_download_reports_progress_and_verified_checksum(self):
        window = self.window()
        window.update = UpdateInfo('0.2.1', 'https://example.com/exe', 'https://example.com/hash', '')
        window.updater.download.return_value = Path('setup.exe')
        window.updater.verified_checksum = 'a' * 64
        with patch('core.updater.app.create_session', return_value=Path('session')), patch.object(window, 'start_worker') as start:
            window.primary_action()
        worker = MagicMock()
        self.assertEqual(start.call_args.args[1](worker), (Path('setup.exe'), 'a' * 64))
        call = window.updater.download.call_args.args
        self.assertEqual(call[:2], (window.update, worker.progress.emit))
        call[2]()
        worker.status.emit.assert_called_once_with('updater.verifying')
        self.assertEqual(call[3], Path('session'))

    def test_thread_executes_operation_off_gui_thread(self):
        window = self.window()
        worker = UpdateWorker(lambda worker: __import__('threading').get_ident(), window)
        worker.start()
        self.assertTrue(worker.wait(1000))
        self.assertIsNone(worker.error)
        self.assertNotEqual(worker.result, __import__('threading').get_ident())

    def test_localization_complete_in_both_languages(self):
        english = Localization('en')
        hebrew = Localization('he')
        keys = [key for key in english.strings if key.startswith('updater.')]
        self.assertGreater(len(keys), 20)
        for key in keys + ['settings.section.updates']:
            self.assertIn(key, hebrew.strings)
        self.assertTrue(hebrew.rtl)
        window = self.window(language='he')
        self.assertEqual(window.layoutDirection(), Qt.RightToLeft)
        self.assertEqual(window.close_button.text(), 'סגירה')


class MainIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_source_and_frozen_launch_commands(self):
        frozen = updater_command('he', True, frozen=True, executable=PROJECT_ROOT / 'installed/PySnips.exe', pid=123)
        self.assertEqual(Path(frozen[0]), PROJECT_ROOT / 'installed/PySnipsUpdater.exe')
        self.assertEqual(frozen[1], '--check-silent')
        self.assertEqual(frozen[-1], '123')
        source = updater_command('en', frozen=False, executable=PROJECT_ROOT / '.venv/Scripts/python.exe', pid=123)
        self.assertEqual(source[1:4], ['-m', 'core.updater', '--check'])
        self.assertIn(str(PROJECT_ROOT / 'main.py'), source)

    def test_process_normal_close_crash_and_restart_protocol(self):
        owner = QApplication.instance()
        launcher = UpdaterProcess(Localization('en'), MagicMock(), owner)
        self.addCleanup(launcher.deleteLater)
        requested = []
        launcher.restart_requested.connect(lambda: requested.append(True))
        launcher.finished(0, QProcess.NormalExit)
        launcher.finished(1, QProcess.NormalExit)
        launcher.finished(RESTART_UPDATE_EXIT_CODE, QProcess.CrashExit)
        self.assertEqual(requested, [])
        launcher.finished(RESTART_UPDATE_EXIT_CODE, QProcess.NormalExit)
        self.assertEqual(requested, [True])

    def test_launcher_lifetime_async_failure_and_duplicate_prevention(self):
        messages = MagicMock()
        launcher = UpdaterProcess(Localization('he'), messages, self.app)
        self.addCleanup(launcher.deleteLater)
        with patch.object(launcher.process, 'start') as start:
            launcher.launch()
        self.assertEqual(start.call_args.args[1][2], '--check')
        launcher.failed(QProcess.FailedToStart)
        messages.error_key.assert_called_once_with('updater.launch_error')
        with patch.object(launcher.process, 'state', return_value=QProcess.Running), patch.object(launcher.process, 'start') as start:
            launcher.launch()
        start.assert_not_called()

    def test_settings_button_language_current_version_timer_and_quit(self):
        with tempfile.TemporaryDirectory() as directory, patch('core.ui.main_window.QApplication.quit') as quit_app:
            for language in ('en', 'he'):
                localization = Localization(language)
                window = MainWindow(SnippetLibrary(Path(directory)), Settings(language), localization, ThemeManager(self.app))
                self.addCleanup(window.deleteLater)
                self.assertIs(window.updater_process.parent(), window)
                with patch.object(window.updater_process.process, 'start') as start:
                    button = window.settings_screen.ui.findChild(QPushButton, 'check_updates')
                    self.assertEqual(button.text(), localization.text('updater.check'))
                    button.click()
                    self.assertIn('--check', start.call_args.args[1])
                    self.assertIn(language, start.call_args.args[1])
                label = window.settings_screen.ui.findChild(QLabel, 'update_version')
                self.assertEqual(label.text(), localization.text('updater.current_version', version=read_version()))
                window.show()
                self.assertEqual(window.update_timer.interval(), 4000)
                self.assertTrue(window.update_timer.isSingleShot())
                with patch.object(window.updater_process, 'launch') as launched:
                    window.update_timer.timeout.emit()
                launched.assert_called_once_with(silent=True)
                window.update_timer.stop()
                window.updater_process.finished(0, QProcess.NormalExit)
                quit_app.assert_not_called()
                window.updater_process.finished(RESTART_UPDATE_EXIT_CODE, QProcess.NormalExit)
                quit_app.assert_called_once_with()
                quit_app.reset_mock()
                window.close()

    def test_main_entry_has_no_backend_import(self):
        import ast
        for path in [PROJECT_ROOT / 'main.py', *(PROJECT_ROOT / 'core/ui').rglob('*.py'), PROJECT_ROOT / 'core/common/update_process.py']:
            tree = ast.parse(path.read_text(encoding='utf-8-sig'))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or '').startswith('core.updater'), str(path))


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.session = self.root / 'update-session-test'
        self.session.mkdir()
        self.installer = self.session / 'PySnips-0.2.1-Setup.exe'
        self.installer.write_bytes(b'verified')
        self.app = self.root / 'install folder/PySnips.exe'
        self.app.parent.mkdir()
        self.app.touch()
        self.args = Namespace(session=str(self.session), installer=str(self.installer), target_version='0.2.1',
                              checksum=hashlib.sha256(b'verified').hexdigest(), app_path=str(self.app),
                              app_pid=123, updater_pid=456)

    def test_frozen_copy_is_own_executable_and_dev_never_copies_python(self):
        own = self.root / 'own.exe'
        own.write_bytes(b'onefile')
        for frozen in (True, False):
            with patch('core.updater.handoff.shutil.copy2', wraps=__import__('shutil').copy2) as copied:
                command = temporary_command(self.session, self.installer, '0.2.1', self.args.checksum,
                                            self.app, 123, 'he', frozen=frozen, executable=own, updater_pid=456)
            self.assertIn('--apply-update', command)
            self.assertIn(self.args.checksum, command)
            self.assertIn('456', command)
            if frozen:
                copied.assert_called_once_with(own, self.session / 'PySnipsUpdater.exe')
                self.assertEqual(Path(command[0]).read_bytes(), b'onefile')
            else:
                copied.assert_not_called()
                self.assertEqual(command[:3], [str(own), '-m', 'core.updater'])

    def test_apply_waits_then_installs_and_restarts(self):
        actions = []
        run = MagicMock(side_effect=lambda *args, **kwargs: actions.append('install') or Namespace(returncode=0))
        launch = MagicMock(side_effect=lambda *args, **kwargs: actions.append('restart'))
        apply_update(self.args, actions.append, wait=lambda pid: actions.append(pid), run=run, launch=launch)
        self.assertEqual(actions, ['updater.waiting', 456, 123, 'updater.installing', 'install', 'updater.restarting', 'restart'])
        command = run.call_args.args[0]
        for switch in ('/VERYSILENT', '/SUPPRESSMSGBOXES', '/SP-', '/NORESTART', '/NOCLOSEAPPLICATIONS', '/NORESTARTAPPLICATIONS'):
            self.assertIn(switch, command)
        self.assertIn('/DIR=' + str(self.app.parent), command)
        self.assertGreater(run.call_args.kwargs['timeout'], 0)
        self.assertEqual(launch.call_args.args[0], [str(self.app)])
        self.assertTrue((self.session / 'coordinator.ready').exists())

    def test_install_failure_or_timeout_does_not_restart(self):
        import subprocess
        for error, code in ((None, 1), (None, 3010), (subprocess.TimeoutExpired('setup', 1), None), (OSError('cannot execute'), None)):
            run = MagicMock(return_value=Namespace(returncode=code), side_effect=error)
            launch = MagicMock()
            with self.subTest(error=error, code=code), self.assertRaises(UpdateError):
                apply_update(self.args, MagicMock(), wait=MagicMock(), run=run, launch=launch)
            launch.assert_not_called()

    def test_installer_timeout_never_kills_setup(self):
        import subprocess
        with patch('core.updater.handoff.subprocess.Popen') as process:
            process.return_value.wait.side_effect = subprocess.TimeoutExpired('setup', 10)
            with self.assertRaises(subprocess.TimeoutExpired):
                run_installer(['setup.exe'], timeout=10, env={})
            process.return_value.kill.assert_not_called()
            process.return_value.terminate.assert_not_called()

    def test_missing_wrong_extension_and_changed_checksum_do_not_run(self):
        for path in (self.session / 'missing.exe', self.session / 'setup.part'):
            self.args.installer = str(path)
            run = MagicMock()
            with self.assertRaises(UpdateError):
                apply_update(self.args, MagicMock(), wait=MagicMock(), run=run)
            run.assert_not_called()
        self.args.installer = str(self.installer)
        self.installer.write_bytes(b'changed')
        with self.assertRaisesRegex(UpdateError, 'checksum mismatch'):
            apply_update(self.args, MagicMock(), wait=MagicMock(), run=MagicMock())

    def test_changed_during_wait_and_cancelled_handoff_do_not_run(self):
        run = MagicMock()
        with self.assertRaisesRegex(UpdateError, 'checksum mismatch'):
            apply_update(self.args, MagicMock(), wait=lambda pid: self.installer.write_bytes(b'changed'), run=run)
        run.assert_not_called()
        self.installer.write_bytes(b'verified')
        (self.session / 'handoff.cancelled').touch()
        with self.assertRaisesRegex(UpdateError, 'cancelled'):
            apply_update(self.args, MagicMock(), wait=MagicMock(), run=run)
        run.assert_not_called()

    def test_source_coordinator_does_not_overwrite_source_tree(self):
        self.args.app_path = str(self.root / 'main.py')
        run = MagicMock()
        with self.assertRaisesRegex(UpdateError, 'Source mode'):
            apply_update(self.args, MagicMock(), wait=MagicMock(), run=run)
        run.assert_not_called()

    def test_bounded_wait_without_real_sleep(self):
        alive = MagicMock(side_effect=[True, True, False])
        pause = MagicMock()
        wait_for_process(123, alive=alive, clock=MagicMock(side_effect=[0, 1, 2]), pause=pause)
        self.assertEqual(pause.call_count, 2)
        with self.assertRaisesRegex(UpdateError, 'Timed out'):
            wait_for_process(123, timeout=1, alive=lambda pid: True, clock=MagicMock(side_effect=[0, 2]), pause=pause)

    def test_wait_failure_never_runs_installer(self):
        run = MagicMock()
        with self.assertRaises(UpdateError):
            apply_update(self.args, MagicMock(), wait=MagicMock(side_effect=UpdateError('timeout')), run=run)
        run.assert_not_called()

    def test_unknown_windows_process_status_is_not_treated_as_exit(self):
        from core.updater.handoff import process_alive
        kernel = MagicMock()
        kernel.WaitForSingleObject.return_value = 0xffffffff
        with patch('core.updater.handoff.sys.platform', 'win32'), patch('core.updater.handoff._windows_process', return_value=(kernel, 123)):
            with self.assertRaises(OSError):
                process_alive(456)
        kernel.CloseHandle.assert_called_once_with(123)

    def test_launch_failure_never_reports_success(self):
        with patch('core.updater.handoff.subprocess.Popen', side_effect=OSError('failed')):
            with self.assertRaises(UpdateError):
                launch_temporary(self.session, self.installer, '0.2.1', self.args.checksum, self.app, 123, 'he')

    def test_handoff_waits_for_coordinator_readiness(self):
        def launched(*args, **kwargs):
            (self.session / 'coordinator.ready').touch()
            return MagicMock()
        with patch('core.updater.handoff.subprocess.Popen', side_effect=launched) as launch:
            launch_temporary(self.session, self.installer, '0.2.1', self.args.checksum, self.app, 123, 'he')
        self.assertIn('--apply-update', launch.call_args.args[0])
        self.assertEqual(launch.call_args.kwargs['env']['PYINSTALLER_RESET_ENVIRONMENT'], '1')

    def test_early_coordinator_exit_marks_cancelled(self):
        with patch('core.updater.handoff.subprocess.Popen') as launch:
            launch.return_value.poll.return_value = 1
            with self.assertRaises(UpdateError):
                launch_temporary(self.session, self.installer, '0.2.1', self.args.checksum, self.app, 123, 'he')
        self.assertTrue((self.session / 'handoff.cancelled').exists())

    def test_stale_cleanup_skips_current_live_and_recent(self):
        import os
        root = self.root / 'cleanup'
        root.mkdir()
        for name in ('current', 'live', 'stale', 'recent'):
            path = root / ('update-session-' + name)
            path.mkdir()
            (path / 'owner.pid').write_text('123' if name == 'live' else '456')
            os.utime(path, (1, 1))
        os.utime(root / 'update-session-recent', (1000000, 1000000))
        with patch('core.updater.handoff.session_root', return_value=root), patch('core.updater.handoff.process_alive', side_effect=lambda pid: pid == 123):
            cleanup_stale(root / 'update-session-current', now=1000000)
        self.assertFalse((root / 'update-session-stale').exists())
        for name in ('current', 'live', 'recent'):
            self.assertTrue((root / ('update-session-' + name)).is_dir())

    def test_session_unique_and_cleanup_failure_ignored(self):
        with patch('core.updater.handoff.session_root', return_value=self.root):
            first, second = create_session(), create_session()
            self.assertNotEqual(first, second)
            self.assertTrue((first / 'owner.pid').exists())
            with patch.object(Path, 'glob', side_effect=OSError('denied')):
                cleanup_stale()


class VersionTests(unittest.TestCase):
    def test_shared_version_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'version.json'
            for value in ('0.2.0', '0.10.3'):
                path.write_text(json.dumps({'version': value}))
                self.assertEqual(read_version(path), value)
            for value in ('v0.2.0', '0.2', '0.02.0', '0.2.1-beta', 1, None):
                path.write_text(json.dumps({'version': value}))
                with self.assertRaises(VersionError):
                    read_version(path)
