"""Standalone Qt updater. All network and installation work runs in its worker."""
import argparse
import math
from pathlib import Path
import sys
import time
import subprocess

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QLabel, QPlainTextEdit, QProgressBar,
                               QPushButton, QVBoxLayout, QHBoxLayout, QWidget)

from core.common.paths import ASSETS_DIR, PROJECT_ROOT
from core.common.update_process import RESTART_UPDATE_EXIT_CODE
from core.localization.localization import Localization
from core.updater.handoff import apply_update, cleanup_stale, create_session, launch_temporary
from core.updater.updater import Updater

MIN_DOWNLOAD_SECONDS = 2.0


def remaining_download_ms(started, now):
    return max(0, math.ceil((MIN_DOWNLOAD_SECONDS - (now - started)) * 1000))


def parser():
    arguments = argparse.ArgumentParser(description='PySnips updater')
    mode = arguments.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--check-silent', action='store_true')
    mode.add_argument('--apply-update', action='store_true')
    arguments.add_argument('--language', choices=('en', 'he'), default='en')
    arguments.add_argument('--app-path', default=str(
        Path(sys.executable).parent / 'PySnips.exe' if getattr(sys, 'frozen', False)
        else PROJECT_ROOT / 'main.py'))
    arguments.add_argument('--app-pid', type=int, default=0)
    arguments.add_argument('--updater-pid', type=int)
    arguments.add_argument('--session')
    arguments.add_argument('--installer')
    arguments.add_argument('--target-version')
    arguments.add_argument('--checksum')
    return arguments


class UpdateWorker(QThread):
    progress = Signal(object, object)
    status = Signal(str)

    def __init__(self, operation, parent):
        super().__init__(parent)
        self.operation = operation
        self.result = None
        self.error = None

    def run(self):
        try:
            self.result = self.operation(self)
        except Exception as error:
            # Boundary for worker errors: never let a failed update close the application.
            self.error = error


class UpdaterWindow(QWidget):
    def __init__(self, args, *, updater=None, clock=time.monotonic):
        super().__init__()
        self.args, self.clock = args, clock
        self.localization = Localization(args.language)
        self.updater = updater or Updater()
        self.worker = None
        self.busy = False
        self.stage = 'check'
        self.session = None
        self.update = None
        self.installer = None
        self.checksum = None
        self.exit_code = 0
        self.setWindowTitle(self.text('updater.title'))
        self.setWindowIcon(QIcon(str(ASSETS_DIR / 'icons/pysnips-multisize.ico')))
        self.setLayoutDirection(Qt.RightToLeft if self.localization.rtl else Qt.LeftToRight)
        self.resize(520, 300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(16)
        self.heading = QLabel()
        self.heading.setObjectName('heading')
        self.heading.setWordWrap(True)
        self.details = QLabel()
        self.details.setObjectName('details')
        self.details.setTextFormat(Qt.PlainText)
        self.details.setWordWrap(True)
        self.heading.setTextFormat(Qt.PlainText)
        self.notes = QPlainTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setMaximumHeight(180)
        self.progress = QProgressBar()
        self.progress.setLayoutDirection(Qt.LeftToRight)
        self.bytes = QLabel()
        self.bytes.setLayoutDirection(Qt.LeftToRight)
        for widget in (self.heading, self.details, self.notes, self.progress, self.bytes):
            layout.addWidget(widget)
        layout.addStretch()
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.primary = QPushButton()
        self.primary.setObjectName('primary')
        self.close_button = QPushButton(self.text('updater.close'))
        buttons.addWidget(self.primary)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)
        self.close_button.clicked.connect(self.close)
        self.primary.clicked.connect(self.primary_action)
        self.ready_timer = QTimer(self)
        self.ready_timer.setSingleShot(True)
        self.ready_timer.setTimerType(Qt.PreciseTimer)
        self.ready_timer.timeout.connect(self.show_ready)
        self.notes.hide()
        self.progress.hide()
        self.bytes.hide()
        self.primary.hide()
        stylesheet = ASSETS_DIR / 'updater.qss'
        if stylesheet.is_file():
            self.setStyleSheet(stylesheet.read_text(encoding='utf-8'))

    def text(self, key, **values):
        return self.localization.text(key, **values)

    def set_busy(self, value):
        self.busy = value
        self.primary.setEnabled(not value)
        self.close_button.setEnabled(not value)

    def start_worker(self, stage, operation):
        self.stage = stage
        self.set_busy(True)
        self.worker = UpdateWorker(operation, self)
        self.worker.progress.connect(self.report_progress)
        self.worker.status.connect(self.show_status)
        self.worker.finished.connect(self.completed)
        self.worker.start()

    def start(self):
        if self.args.apply_update:
            self.show()
            self.start_worker('apply', lambda worker: apply_update(self.args, worker.status.emit))
        else:
            self.heading.setText(self.text('updater.checking'))
            if not self.args.check_silent:
                self.show()
            self.start_worker('check', lambda worker: (self.updater.current_version, self.updater.check()))

    def show_status(self, key):
        self.heading.setText(self.text(key))

    def completed(self):
        worker = self.worker
        self.set_busy(False)
        if worker.error is not None:
            if self.stage == 'check' and self.args.check_silent:
                QApplication.exit(0)
                return
            self.show_error(worker.error)
            return
        if self.stage == 'check':
            version, self.update = worker.result
            self.details.setText(self.text('updater.current_version', version=version))
            if self.update is None:
                if self.args.check_silent:
                    QApplication.exit(0)
                    return
                self.heading.setText(self.text('updater.up_to_date'))
            else:
                self.heading.setText(self.text('updater.available', version=self.update.version))
                self.primary.setText(self.text('updater.download_install').replace('&', '&&'))
                self.close_button.setText(self.text('updater.later'))
                self.primary.show()
                if self.update.release_notes:
                    self.notes.setPlainText(self.update.release_notes)
                    self.notes.show()
            self.show()
        elif self.stage == 'download':
            self.installer, self.checksum = worker.result
            # Real download/verification have finished. Delay only the ready transition.
            self.set_busy(True)
            self.ready_timer.start(remaining_download_ms(self.download_started, self.clock()))
        elif self.stage == 'handoff':
            self.exit_code = RESTART_UPDATE_EXIT_CODE
            QApplication.exit(self.exit_code)
        elif self.stage == 'apply':
            QApplication.exit(0)

    def show_error(self, error):
        failed_stage = self.stage
        self.stage = 'error'
        self.exit_code = 1
        self.heading.setText(self.text('updater.failed'))
        key = {'check': 'updater.check_error', 'download': 'updater.download_error',
               'handoff': 'updater.handoff_error', 'apply': 'updater.install_error'}[failed_stage]
        if isinstance(error, Exception) and isinstance(error.__cause__, subprocess.TimeoutExpired):
            key = 'updater.install_timeout'
        self.details.setText(self.text(key) + '\n\n' + self.text('updater.error_detail', detail=str(error)))
        self.primary.hide()
        self.progress.hide()
        self.bytes.hide()
        self.close_button.setText(self.text('updater.close'))
        self.show()

    def primary_action(self):
        if self.busy:
            return
        if self.stage == 'check' and self.update:
            try:
                self.session = create_session()
            except OSError as error:
                self.stage = 'download'
                self.show_error(error)
                return
            self.download_started = self.clock()
            self.heading.setText(self.text('updater.downloading', version=self.update.version))
            self.notes.hide()
            self.progress.setRange(0, 0)
            self.progress.show()
            self.bytes.show()
            self.close_button.setText(self.text('updater.close'))

            def download(worker):
                path = self.updater.download(self.update, worker.progress.emit,
                                            lambda: worker.status.emit('updater.verifying'), self.session)
                return path, self.updater.verified_checksum

            self.start_worker('download', download)
        elif self.stage == 'ready':
            if Path(self.args.app_path).suffix.lower() != '.exe':
                self.stage = 'handoff'
                self.show_error(ValueError(self.text('updater.source_install_error')))
                return
            self.heading.setText(self.text('updater.preparing'))
            self.start_worker('handoff', lambda worker: launch_temporary(
                self.session, self.installer, self.update.version, self.checksum,
                self.args.app_path, self.args.app_pid, self.args.language))

    def report_progress(self, downloaded, total):
        if total is None:
            self.progress.setRange(0, 0)
            self.bytes.setText(f'{downloaded / 1048576:.1f} MB')
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(min(100, downloaded * 100 // total))
            self.bytes.setText(f'{downloaded / 1048576:.1f} MB / {total / 1048576:.1f} MB')

    def show_ready(self):
        # Even if a platform timer wakes early, the minimum visible duration is exact.
        if hasattr(self, 'download_started'):
            remaining = remaining_download_ms(self.download_started, self.clock())
            if remaining:
                self.ready_timer.start(remaining)
                return
        self.stage = 'ready'
        self.set_busy(False)
        self.heading.setText(self.text('updater.ready'))
        self.primary.setText(self.text('updater.restart_update').replace('&', '&&'))
        self.progress.hide()
        self.bytes.hide()

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
            return
        event.accept()
        QApplication.exit(self.exit_code)


def main(argv=None):
    arguments = parser()
    args = arguments.parse_args(argv)
    if args.apply_update and any(getattr(args, key) is None for key in (
            'session', 'installer', 'target_version', 'checksum', 'updater_pid')):
        arguments.error('apply-update requires a complete update session')
    app = QApplication([sys.argv[0]])
    app.setApplicationName('PySnipsUpdater')
    app.setQuitOnLastWindowClosed(False)
    cleanup_stale(args.session)
    window = UpdaterWindow(args)
    QTimer.singleShot(0, window.start)
    return app.exec()
