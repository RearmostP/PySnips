from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton, QLabel
from core.common.paths import PROJECT_ROOT
from core.localization.localization import Localization
from core.settings.settings import Settings
from core.snips.library import SnippetLibrary
from core.theme.theme_manager import ThemeManager
from core.ui.main_window import MainWindow
from core.ui.snips.dialogs.create_snippet import CreateSnippet
from core.ui.snips.dialogs.snippet_details import SnippetDetails
from core.ui.snips.dialogs.deleted_snippets import DeletedSnippets


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.library = SnippetLibrary(Path(self.temp.name))
        self.localization = Localization('he')
        self.themes = ThemeManager(self.app)
        self.themes.apply('dark')
        self.window = MainWindow(self.library, Settings('he'), self.localization, self.themes)
        self.addCleanup(self.window.close)

    def test_navigation_and_startup(self):
        self.assertEqual(self.window.stack.count(), 3)
        self.assertIs(self.window.stack.currentWidget(), self.window.home)
        self.window.home.ui.findChild(QPushButton, 'open_snips').click()
        self.assertIs(self.window.stack.currentWidget(), self.window.snips)
        self.window.show_settings()
        self.assertIs(self.window.stack.currentWidget(), self.window.settings_screen)
        self.assertEqual(self.window.home.ui.findChild(QPushButton, 'open_snips').text(), self.localization.text('nav.snips'))
        other = MainWindow(self.library, Settings('he', 'dark', True), self.localization, self.themes)
        self.assertIs(other.stack.currentWidget(), other.snips)
        other.close()

    def test_create_edit_details_and_trash_dialogs(self):
        dialog = CreateSnippet(self.library, self.localization, self.window.messages, parent=self.window)
        dialog.title.setText('UI example')
        dialog.content.setPlainText('```python\nprint(123)\n```')
        dialog.tags.setText('ui, qt')
        dialog.save()
        self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)
        s = dialog.snippet
        edit = CreateSnippet(self.library, self.localization, self.window.messages, s, self.window)
        edit.title.setText('Edited')
        edit.category.setCurrentText('PySide6')
        edit.save()
        self.assertEqual(self.library.load(s.id).category, 'PySide6')
        details = SnippetDetails(self.library, self.localization, self.window.messages, edit.snippet, self.window)
        self.assertEqual(details.ui.findChild(QLabel, 'title').text(), 'Edited')
        self.library.delete(s.id)
        trash = DeletedSnippets(self.library, self.localization, self.window.messages, self.window)
        self.assertEqual(trash.items.count(), 1)
        trash.items.setCurrentRow(0)
        trash.restore()
        self.assertEqual(trash.items.count(), 0)
        self.assertEqual(self.library.load(s.id).title, 'Edited')

    def test_live_settings_and_theme(self):
        with patch('core.ui.main_window.save_settings') as save:
            self.window.apply_settings(Settings('en', 'light', True))
            save.assert_called_once()
        self.assertEqual(self.window.layoutDirection(), Qt.LayoutDirection.LeftToRight)
        self.assertEqual(self.window.home.ui.findChild(QPushButton, 'open_snips').text(), self.localization.text('nav.snips'))
        self.assertEqual(self.themes.current, 'light')

    def test_designer_translation_keys_resolve(self):
        import xml.etree.ElementTree as ET
        for path in (PROJECT_ROOT / 'core' / 'ui').rglob('*.ui'):
            root = ET.parse(path)
            for prop in root.findall('.//property'):
                if prop.attrib['name'].startswith('i18n'):
                    key = prop.findtext('string')
                    self.assertIn(key, self.localization.english, str(path))
                    self.assertIn(key, self.localization.strings, str(path))

    def test_category_sidebar_and_global_search(self):
        first = self.library.create('Python example', 'Python', 'firstword')
        second = self.library.create('Qt example', 'PySide6', 'secondword')
        self.window.show_snips()
        self.window.snips.select_category('Python')
        self.assertEqual(len(self.window.snips.cards), 1)
        self.assertEqual(self.window.snips.cards[0].title.text(), first.title)
        self.window.snips.search.query.setText('secondword')
        self.window.snips.refresh()
        self.assertEqual(len(self.window.snips.cards), 1)
        self.assertEqual(self.window.snips.cards[0].title.text(), second.title)
        with patch.object(self.window.snips, 'open_snippet') as opened:
            card = self.window.snips.cards[0]
            # The signal is tested separately from a blocking modal dialog.
            received = []
            card.details_requested.connect(received.append)
            card.ui.findChild(QPushButton, 'details').click()
            self.assertEqual(received, [second.id])

    def test_editor_toolbar_and_preview(self):
        dialog = CreateSnippet(self.library, self.localization, self.window.messages, parent=self.window)
        dialog.content.setPlainText('example')
        dialog.content.selectAll()
        dialog.ui.findChild(QPushButton, 'bold').click()
        self.assertEqual(dialog.content.toPlainText(), '**example**')
        dialog.show_preview()
        self.assertEqual(dialog.content_stack.currentIndex(), 1)
        self.assertIn('example', dialog.preview.toPlainText())
        dialog.show_preview()
        self.assertEqual(dialog.content_stack.currentIndex(), 0)
