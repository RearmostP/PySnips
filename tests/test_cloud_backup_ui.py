from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton
from core.localization.localization import Localization
from core.snips.library import SnippetLibrary
from core.ui.dialogs.cloud_backup import CloudBackupDialog
from core.ui.main_window import MainWindow
from core.settings.settings import Settings
from core.theme.theme_manager import ThemeManager


class CloudBackupUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.library = SnippetLibrary(Path(self.temp.name))
        self.localization = Localization('en')
        self.messages = MagicMock()
        self.provider = MagicMock()
        self.provider.connected = False
        self.provider.resume.return_value = False
        self.provider.list_backups.return_value = []
        self.dialog = CloudBackupDialog(self.library, self.localization, self.messages, provider=self.provider)
        self.addCleanup(self.dispose)
        self.wait()

    def wait(self):
        deadline = time.monotonic() + 5
        self.app.processEvents()
        while self.dialog.worker is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.app.processEvents()
        self.assertIsNone(self.dialog.worker)

    def dispose(self):
        self.wait()
        self.dialog.close()
        self.dialog.deleteLater()
        self.app.processEvents()

    def test_states_and_rtl_complete_localization(self):
        self.assertEqual(self.dialog.state.text(), 'Not connected')
        self.assertFalse(self.dialog.connect_button.isHidden())
        self.assertTrue(self.dialog.backup_button.isHidden())
        self.provider.connected = True
        self.dialog.render()
        self.assertEqual(self.dialog.state.text(), 'Connected')
        self.assertTrue(self.dialog.connect_button.isHidden())
        self.assertFalse(self.dialog.backup_button.isHidden())
        english = {k for k in self.localization.english if k.startswith('backup.')}
        hebrew = Localization('he')
        self.assertEqual(english, {k for k in hebrew.strings if k.startswith('backup.')})
        for key in english:
            self.assertNotIn('????', hebrew.strings[key])
        other = CloudBackupDialog(self.library, hebrew, self.messages, provider=self.provider)
        self.assertEqual(other.layoutDirection(), Qt.RightToLeft)
        other.close()
        # Its deferred initial resume must finish before destruction.
        deadline = time.monotonic() + 5
        self.app.processEvents()
        while other.worker is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        other.close()

    def test_backup_and_restore_off_gui_thread_and_confirmation(self):
        self.provider.connected = True
        self.dialog.render()
        self.library.create('Original', 'Python', 'content')
        gui = threading.get_ident()
        worker_threads = []
        archives = []
        def upload(archive, progress):
            worker_threads.append(threading.get_ident())
            self.assertTrue(Path(archive).is_file())
            archives.append(Path(archive).read_bytes())
            progress(50)
        self.provider.upload.side_effect = upload
        backup = {'id': 'chosen', 'createdTime': '2026-10-10T22:30:00Z', 'size': '1048576'}
        self.provider.list_backups.return_value = [backup]
        self.dialog.backup_button.click()
        self.assertFalse(self.dialog.backup_button.isEnabled())
        self.dialog.reject()
        self.wait()
        self.assertEqual(self.dialog.items.count(), 1)
        self.dialog.items.setCurrentRow(0)
        self.messages.confirm.return_value = False
        self.dialog.restore_button.click()
        self.provider.download.assert_not_called()
        self.messages.confirm.assert_called_once_with(self.localization.text('backup.confirmation'))
        self.library.create('Extra', 'Python', 'extra')
        def download(backup_id, destination):
            worker_threads.append(threading.get_ident())
            Path(destination).write_bytes(archives[0])
            return destination
        self.provider.download.side_effect = download
        self.messages.confirm.return_value = True
        restored = []
        self.dialog.restored.connect(lambda: restored.append(threading.get_ident()))
        self.dialog.restore_button.click()
        self.wait()
        self.assertEqual([s.title for s in self.library.list()], ['Original'])
        self.assertEqual(restored, [gui])
        self.assertTrue(all(thread != gui for thread in worker_threads))
        self.assertEqual(len(worker_threads), 2)
        self.assertEqual(self.dialog.status.text(), self.localization.text('backup.restore_complete'))

    def test_settings_single_row_manage_opens_dialog_refreshes(self):
        themes = ThemeManager(self.app)
        with patch('core.common.update_process.UpdaterProcess.launch'):
            window = MainWindow(self.library, Settings(), self.localization, themes)
        try:
            buttons = window.settings_screen.ui.findChildren(QPushButton, 'cloud_manage')
            self.assertEqual(len(buttons), 1)
            with patch('core.ui.settings.settings_screen.CloudBackupDialog') as dialog:
                buttons[0].click()
                dialog.assert_called_once_with(self.library, self.localization, window.messages, window.settings_screen)
                dialog.return_value.exec.assert_called_once()
                dialog.return_value.restored.connect.assert_called_once()
            self.library.add_category('Restored category')
            window.settings_screen.library_restored.emit()
            self.assertIn('Restored category', [name for name, _ in window.snips.category_buttons])
        finally:
            window.update_timer.stop()
            window.close()
