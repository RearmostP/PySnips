"""Only the updater launch command and its explicit exit protocol live in PySnips."""
import os
from pathlib import Path
import sys

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from core.common.paths import PROJECT_ROOT

RESTART_UPDATE_EXIT_CODE = 42


def updater_command(language, silent=False, *, frozen=None, executable=None, root=PROJECT_ROOT, pid=None):
    frozen = getattr(sys, 'frozen', False) if frozen is None else frozen
    executable = Path(executable or sys.executable).resolve()
    app_path = executable if frozen else Path(root).resolve() / 'main.py'
    command = [str(executable.parent / 'PySnipsUpdater.exe')] if frozen else [str(executable), '-m', 'core.updater']
    return command + [
        '--check-silent' if silent else '--check', '--language', language,
        '--app-path', str(app_path), '--app-pid', str(os.getpid() if pid is None else pid),
    ]


class UpdaterProcess(QObject):
    restart_requested = Signal()

    def __init__(self, localization, messages, parent):
        super().__init__(parent)
        self.localization, self.messages = localization, messages
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(PROJECT_ROOT))
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert('PYINSTALLER_RESET_ENVIRONMENT', '1')
        self.process.setProcessEnvironment(environment)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.failed)

    def launch(self, silent=False):
        if self.process.state() != QProcess.NotRunning:
            return
        command = updater_command(self.localization.language, silent)
        self.process.start(command[0], command[1:])

    def finished(self, code, status):
        if status == QProcess.NormalExit and code == RESTART_UPDATE_EXIT_CODE:
            self.restart_requested.emit()

    def failed(self, error):
        if error == QProcess.FailedToStart:
            self.messages.error_key('updater.launch_error')
