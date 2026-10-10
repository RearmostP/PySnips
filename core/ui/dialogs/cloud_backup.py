"""Modal library access boundary; one small worker for blocking operations."""
from datetime import datetime
from pathlib import Path
import tempfile

from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtWidgets import (QDialog, QLabel, QPushButton, QVBoxLayout,
                               QHBoxLayout, QListWidget, QProgressBar)

from core.backup.backup_manager import BackupManager, BackupError
from core.backup.google_drive import GoogleDrive


class BackupWorker(QThread):
    status = Signal(str)
    progress = Signal(int)

    def __init__(self, operation, parent):
        super().__init__(parent)
        self.setObjectName('CloudBackupDialog')
        self.operation, self.result, self.error = operation, None, None

    def run(self):
        try:
            self.result = self.operation(self)
        except BackupError as error:
            self.error = str(error)
        except Exception:
            self.error = 'local'


class CloudBackupDialog(QDialog):
    restored = Signal()

    def __init__(self, library, localization, messages, parent=None, *, provider=None):
        super().__init__(parent)
        self.library, self.localization, self.messages = library, localization, messages
        self.provider = provider or GoogleDrive()
        self.manager = BackupManager(library.root.parent.parent)
        self.worker = None
        self.backups = []
        self.setWindowTitle(self.text('title'))
        self.setModal(True)
        self.setLayoutDirection(Qt.RightToLeft if localization.rtl else Qt.LeftToRight)
        self.resize(560, 420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        heading = QLabel(self.text('title'))
        heading.setObjectName('backup_heading')
        layout.addWidget(heading)
        layout.addWidget(QLabel(self.text('google')))
        self.state = QLabel()
        self.state.setTextFormat(Qt.PlainText)
        layout.addWidget(self.state)
        actions = QHBoxLayout()
        self.connect_button = QPushButton(self.text('connect'))
        self.backup_button = QPushButton(self.text('backup'))
        actions.addWidget(self.connect_button)
        actions.addWidget(self.backup_button)
        layout.addLayout(actions)
        layout.addWidget(QLabel(self.text('backups')))
        self.items = QListWidget()
        self.items.setLayoutDirection(Qt.LeftToRight)
        layout.addWidget(self.items)
        self.empty = QLabel(self.text('empty'))
        layout.addWidget(self.empty)
        self.restore_button = QPushButton(self.text('restore'))
        layout.addWidget(self.restore_button)
        self.status = QLabel()
        self.status.setTextFormat(Qt.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setLayoutDirection(Qt.LeftToRight)
        layout.addWidget(self.progress)
        self.disconnect_button = QPushButton(self.text('disconnect'))
        layout.addWidget(self.disconnect_button)
        self.connect_button.clicked.connect(lambda: self.start('connect', lambda w: self._connect()))
        self.disconnect_button.clicked.connect(lambda: self.start('disconnect', lambda w: self.provider.disconnect()))
        self.backup_button.clicked.connect(lambda: self.start('backup', self._backup))
        self.restore_button.clicked.connect(self.confirm_restore)
        self.items.currentRowChanged.connect(self.render)
        self.render()
        QTimer.singleShot(0, self.resume)

    def text(self, key, **values):
        return self.localization.text('backup.' + key, **values)

    def resume(self):
        self.start('list', lambda w: self.provider.list_backups() if self.provider.resume() else [])

    def _connect(self):
        self.provider.connect()
        return self.provider.list_backups()

    def _backup(self, worker):
        worker.status.emit('backing')
        with tempfile.TemporaryDirectory(prefix='pysnips-upload-') as temporary:
            archive = self.manager.create(temporary)
            worker.status.emit('uploading')
            self.provider.upload(archive, worker.progress.emit)
        worker.status.emit('backup_complete')
        return self.provider.list_backups()

    def confirm_restore(self):
        row = self.items.currentRow()
        if self.worker is not None or row < 0 or row >= len(self.backups):
            return
        if self.messages.confirm(self.text('confirmation')):
            backup_id = self.backups[row]['id']
            self.start('restore', lambda worker: self._restore(worker, backup_id))

    def _restore(self, worker, backup_id):
        with tempfile.TemporaryDirectory(prefix='pysnips-download-') as temporary:
            worker.status.emit('downloading')
            archive = self.provider.download(backup_id, Path(temporary) / 'snapshot.zip')
            self.manager.restore(archive, rebuild=self.library.rebuild_search,
                                 status=worker.status.emit)

    def start(self, action, operation):
        if self.worker is not None:
            return
        self.action = action
        self.worker = BackupWorker(operation, self)
        self.worker.status.connect(self.set_status)
        self.worker.progress.connect(self.set_progress)
        self.worker.finished.connect(self.finished_operation)
        self.progress.setRange(0, 0)
        self.status.setText(self.text('busy'))
        self.render()
        self.worker.start()

    def set_status(self, key):
        self.status.setText(self.text(key))
        self.progress.setRange(0, 0)

    def set_progress(self, value):
        self.progress.setRange(0, 100)
        self.progress.setValue(value)

    def finished_operation(self):
        worker = self.worker
        self.worker = None
        if worker.error:
            self.status.setText(self.text('error.' + worker.error))
            self.messages.error(self.status.text())
        else:
            if isinstance(worker.result, list):
                self.backups = worker.result
            if self.action == 'disconnect':
                self.backups = []
            self.status.setText(self.text('backup_complete') if self.action == 'backup'
                                else self.text('restore_complete') if self.action == 'restore' else '')
            if self.action == 'restore':
                self.restored.emit()
                self.messages.info(self.text('restore_complete'))
            elif self.action == 'backup':
                self.messages.info(self.text('backup_complete'))
        worker.deleteLater()
        self.items.clear()
        for backup in self.backups:
            try:
                date = datetime.fromisoformat(backup.get('createdTime', '').replace('Z', '+00:00')).astimezone().strftime('%Y-%m-%d %H:%M')
            except ValueError:
                date = '—'
            try:
                size = self.text('size', size=f"{int(backup['size']) / 1024 ** 2:.1f}")
            except (KeyError, TypeError, ValueError):
                size = '—'
            self.items.addItem(f'{date}    {size}')
        self.render()

    def render(self, *args):
        busy = self.worker is not None
        connected = self.provider.connected
        self.state.setText(self.text('connected' if connected else 'disconnected'))
        self.connect_button.setVisible(not connected)
        self.connect_button.setEnabled(not busy)
        self.backup_button.setVisible(connected)
        self.backup_button.setEnabled(connected and not busy)
        # Also lets the user clear expired/invalid saved authorization.
        self.disconnect_button.setVisible(True)
        self.disconnect_button.setEnabled(not busy)
        self.restore_button.setEnabled(connected and not busy and self.items.currentRow() >= 0)
        self.items.setEnabled(connected and not busy)
        self.empty.setVisible(not self.backups)
        self.progress.setVisible(busy)

    def reject(self):
        if self.worker is None:
            super().reject()

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
        else:
            super().closeEvent(event)
