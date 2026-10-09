from pathlib import Path
from platform import python_version
import tempfile
import json
import unittest
from unittest.mock import patch

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from core.common.user_messages import UserMessageManager
from core.localization.localization import Localization
from core.settings.settings import Settings
from core.snips.library import SnippetLibrary
from core.theme.theme_manager import ThemeManager
from core.ui.dialogs.about_dialog import AboutDialog, GITHUB_URL, FORUM_URL
from core.common.paths import VERSION_FILE
from core.common.version import read_version
from core.ui.settings.settings_screen import SettingsScreen
from core.ui.snips.snips_screen import SnipsScreen


class AboutDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_runtime_information_localization_and_themes(self):
        themes = ThemeManager(self.app)
        themes.apply('dark')
        for language in ('en', 'he'):
            localization = Localization(language)
            dialog = AboutDialog(localization)
            self.addCleanup(dialog.close)
            self.assertEqual(dialog.windowTitle(), localization.text('about.title'))
            for name, key, values in (
                ('version', 'about.version', {'version': json.loads(VERSION_FILE.read_text(encoding='utf-8'))['version']}),
                ('python_version', 'about.python', {'version': python_version()}),
                ('pyside_version', 'about.pyside', {'version': pyside_version}),
                ('creator', 'about.created_by', {'creator': 'RearmostP'}),
            ):
                self.assertEqual(dialog.ui.findChild(QLabel, name).text(), localization.text(key, **values))
            self.assertEqual(dialog.ui.layoutDirection(), Qt.LeftToRight)
            self.assertFalse(dialog.ui.findChild(QLabel, 'app_icon').pixmap().isNull())
            dialog.show()
            for theme in ('dark', 'light'):
                themes.apply(theme)
                self.app.processEvents()
                label = dialog.ui.findChild(QLabel, 'python_version')
                self.assertEqual(label.font().family(), 'Segoe UI')
                self.assertEqual(label.font().pixelSize(), 12)
                self.assertEqual(dialog.width(), 374)
                self.assertTrue(230 <= dialog.height() <= 240)
            dialog.ui.findChild(QPushButton, 'close').click()
            self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)

    def test_version_is_read_from_metadata_each_time(self):
        localization = Localization('en')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'version.json'
            with patch('core.ui.dialogs.about_dialog.read_version', side_effect=lambda: read_version(path)):
                for version in ('0.2.0', '0.2.1'):
                    path.write_text(json.dumps({'version': version}), encoding='utf-8')
                    dialog = AboutDialog(localization)
                    self.addCleanup(dialog.close)
                    self.assertEqual(dialog.ui.findChild(QLabel, 'version').text(),
                                     localization.text('about.version', version=version))

    def test_unreadable_or_invalid_version_does_not_break_about(self):
        localization = Localization('en')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'version.json'
            with patch('core.ui.dialogs.about_dialog.read_version', side_effect=lambda: read_version(path)):
                for content in (None, '{', '{"version": "invalid"}'):
                    if content is not None:
                        path.write_text(content, encoding='utf-8')
                    dialog = AboutDialog(localization)
                    self.addCleanup(dialog.close)
                    self.assertEqual(dialog.ui.findChild(QLabel, 'version').text(),
                                     localization.text('about.version', version='—'))

    def test_links_open_supplied_urls(self):
        dialog = AboutDialog(Localization('en'))
        self.addCleanup(dialog.close)
        with patch('core.ui.dialogs.about_dialog.QDesktopServices.openUrl') as opened:
            dialog.ui.findChild(QPushButton, 'github').click()
            self.assertEqual(opened.call_args.args[0].toString(), GITHUB_URL)
            dialog.ui.findChild(QPushButton, 'forum').click()
            self.assertEqual(opened.call_args.args[0].toEncoded().data().decode(), FORUM_URL)
            self.assertEqual(opened.call_count, 2)

    def test_existing_about_entry_points_open_custom_dialog(self):
        with tempfile.TemporaryDirectory() as directory:
            library = SnippetLibrary(Path(directory))
            localization = Localization('en')
            messages = UserMessageManager(None, localization)
            themes = ThemeManager(self.app)
            settings = SettingsScreen(library, Settings('en'), localization, themes, messages)
            snips = SnipsScreen(library, localization, messages)
            self.addCleanup(settings.close)
            self.addCleanup(snips.close)
            with patch.object(messages, 'info') as info:
                with patch('core.ui.settings.settings_screen.AboutDialog') as dialog:
                    settings.ui.findChild(QPushButton, 'about').click()
                    dialog.assert_called_once_with(localization, settings)
                    dialog.return_value.exec.assert_called_once()
                with patch('core.ui.snips.snips_screen.AboutDialog') as dialog:
                    snips.refresh_categories()
                    snips.menu.actions()[-1].trigger()
                    dialog.assert_called_once_with(localization, snips)
                    dialog.return_value.exec.assert_called_once()
                info.assert_not_called()
