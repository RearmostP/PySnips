from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt, QCoreApplication, QEvent
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
        self.addCleanup(self.dispose_window)

    def dispose_window(self):
        self.app.processEvents()
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(self.window, QEvent.DeferredDelete)

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

    def test_settings_controls_save_immediately(self):
        from core.settings.settings import save_settings, load_settings
        path = Path(self.temp.name) / 'preferences.json'
        screen = self.window.settings_screen
        with patch('core.ui.main_window.save_settings', side_effect=lambda value: save_settings(value, path)) as saved:
            screen.language.setCurrentIndex(screen.language.findData('en'))
            self.assertEqual(saved.call_count, 1)
            self.assertEqual(self.localization.language, 'en')
            screen.theme.setCurrentIndex(screen.theme.findData('light'))
            self.assertEqual(saved.call_count, 2)
            self.assertEqual(self.themes.current, 'light')
            screen.start.setChecked(True)
            self.assertEqual(saved.call_count, 3)
            self.assertEqual(load_settings(path), Settings('en', 'light', True))
            screen.retranslate(self.window.settings)
            self.assertEqual(saved.call_count, 3)
        restarted = MainWindow(self.library, load_settings(path), self.localization, self.themes)
        self.addCleanup(restarted.close)
        self.assertIs(restarted.stack.currentWidget(), restarted.snips)

    def test_settings_save_failure_restores_controls(self):
        screen = self.window.settings_screen
        with patch('core.ui.main_window.save_settings', side_effect=OSError('unwritable')) as saved:
            with patch.object(self.window.messages, 'error_key') as error:
                screen.theme.setCurrentIndex(screen.theme.findData('light'))
                saved.assert_called_once()
                error.assert_called_once_with('errors.io')
        self.assertEqual(screen.theme.currentData(), 'dark')
        self.assertEqual(self.themes.current, 'dark')

    def test_settings_back_returns_to_previous_screen(self):
        back = self.window.settings_screen.ui.findChild(QPushButton, 'back')
        self.assertIsNone(self.window.menuWidget())
        for show, target in [(self.window.show_home, self.window.home),
                             (self.window.show_snips, self.window.snips)]:
            show()
            self.window.show_settings()
            self.window.show_settings()
            self.assertIs(self.window.stack.currentWidget(), self.window.settings_screen)
            back.click()
            self.assertIs(self.window.stack.currentWidget(), target)

    def test_settings_width_and_direction(self):
        from PySide6.QtWidgets import QWidget
        screen = self.window.settings_screen
        body = screen.ui.findChild(QWidget, 'settings_body')
        self.window.show_settings()
        self.window.show()
        with patch('core.ui.main_window.save_settings'):
            for language in ('en', 'he'):
                screen.language.setCurrentIndex(screen.language.findData(language))
                self.app.processEvents()
                self.assertLessEqual(body.width(), 780)
                self.assertGreaterEqual(body.width(), 720)
                title = screen.ui.findChild(QLabel, 'language_title')
                title_x = title.mapTo(screen, title.rect().center()).x()
                control_x = screen.language.mapTo(screen, screen.language.rect().center()).x()
                self.assertEqual(control_x > title_x, language == 'en')
                self.assertEqual(screen.ui.findChild(QPushButton, 'back').text(), self.localization.text('common.back'))
        self.window.resize(640, 480)
        self.app.processEvents()
        self.assertLess(body.width(), 640)

    def test_settings_data_actions_and_single_page(self):
        from PySide6.QtWidgets import QStackedWidget, QScrollArea
        screen = self.window.settings_screen
        self.assertIsNone(screen.ui.findChild(QStackedWidget))
        for name in ('general_button', 'snips_button', 'home', 'snips', 'save'):
            self.assertIsNone(screen.ui.findChild(QPushButton, name))
        self.assertTrue(screen.ui.findChild(QScrollArea, 'settings_scroll').widgetResizable())
        with patch('core.ui.settings.settings_screen.DeletedSnippets') as dialog:
            screen.ui.findChild(QPushButton, 'deleted').click()
            dialog.assert_called_once_with(self.library, self.localization, self.window.messages, screen)
            dialog.return_value.exec.assert_called_once()
        snippet = self.library.create('Index test', 'Python', 'settings_search_word')
        with patch.object(self.library, 'rebuild_search', wraps=self.library.rebuild_search) as rebuild:
            with patch.object(self.window.messages, 'info') as info:
                screen.ui.findChild(QPushButton, 'rebuild').click()
                rebuild.assert_called_once()
                info.assert_called_once_with(self.localization.text('settings.rebuilt'))
        self.assertEqual(self.library.search('settings_search_word')[0].id, snippet.id)

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
        self.assertEqual(self.window.snips.current_category, 'Python')
        for _, button in self.window.snips.category_buttons:
            self.assertFalse(button.isCheckable())
            self.assertFalse(button.isChecked())
            self.assertEqual(button.minimumHeight(), 35)
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

    def test_details_metadata_presentation(self):
        from dataclasses import replace
        from datetime import datetime
        from core.localization.ui_translator import translate_ui
        from PySide6.QtWidgets import QGridLayout
        original = self.library.create('<b>Branch</b>', 'Python', 'content', 'git, branch')
        snippet = replace(original, created_at='2026-10-05T14:22:35+00:00')
        dialog = SnippetDetails(self.library, self.localization, self.window.messages, snippet, self.window)
        self.addCleanup(dialog.close)
        tags = dialog.ui.findChild(QGridLayout, 'tagsLayout')
        self.assertEqual([tags.itemAt(i).widget().text() for i in range(tags.count())], snippet.tags)
        self.assertEqual(dialog.ui.findChild(QLabel, 'title').textFormat(), Qt.PlainText)
        self.assertIsNone(dialog.ui.findChild(QLabel, 'title_label'))
        expected = datetime.fromisoformat(snippet.created_at).astimezone().strftime('%d/%m/%Y %H:%M')
        self.assertEqual(dialog.ui.findChild(QLabel, 'created_at').text(), expected)
        for language, direction in [('en', Qt.LeftToRight), ('he', Qt.RightToLeft)]:
            self.localization.set_language(language)
            translate_ui(dialog, self.localization)
            self.assertEqual(dialog.windowTitle(), self.localization.text('snips.details_title'))
            self.assertEqual(dialog.ui.layoutDirection(), direction)
            for theme in ('light', 'dark'):
                self.themes.apply(theme)
                dialog.ensurePolished()
                self.assertEqual(dialog.ui.findChild(QLabel, 'title').font().pixelSize(), 20)
                self.assertEqual(dialog.ui.findChild(QLabel, 'category').font().family(), 'Segoe UI')
        dialog.snippet = replace(snippet, tags=[], created_at='invalid timestamp')
        dialog.refresh()
        self.assertEqual(tags.count(), 1)
        self.assertEqual(tags.itemAt(0).widget().text(), '—')
        self.assertEqual(dialog.ui.findChild(QLabel, 'created_at').text(), '—')
        long_tag = 'a-very-long-developer-tag-' * 4
        dialog.snippet = replace(snippet, title='A long snippet title ' * 8, tags=[long_tag] * 7)
        dialog.refresh()
        dialog.show()
        self.app.processEvents()
        self.assertEqual(tags.count(), 7)
        self.assertEqual(tags.itemAt(0).widget().toolTip(), long_tag)
        self.assertGreaterEqual(dialog.height(), dialog.layout().totalHeightForWidth(dialog.width()))
        self.assertEqual(self.library.load(original.id).created_at, original.created_at)

    def test_editor_polish_preserves_language_and_theme_switching(self):
        from main import load_fonts
        from core.localization.ui_translator import translate_ui
        load_fonts()
        dialog = CreateSnippet(self.library, self.localization, self.window.messages, parent=self.window)
        self.addCleanup(dialog.close)
        dialog.show()
        self.app.processEvents()
        for language, direction in [('he', Qt.RightToLeft), ('en', Qt.LeftToRight)]:
            self.localization.set_language(language)
            translate_ui(dialog, self.localization)
            self.assertEqual(dialog.ui.layoutDirection(), direction)
            self.assertEqual(dialog.content.layoutDirection(), Qt.LeftToRight)
            for name, key in [('title', 'snips.title'), ('category', 'snips.category'), ('tags', 'snips.tags_label')]:
                label = dialog.ui.findChild(QLabel, name + 'Label')
                self.assertEqual(label.text(), self.localization.text(key))
                self.assertIs(label.buddy(), getattr(dialog, name))
            for theme in ('light', 'dark'):
                self.themes.apply(theme)
                self.app.processEvents()
                self.assertEqual(dialog.content.font().family(), 'JetBrains Mono')
                self.assertEqual(dialog.content.font().pixelSize(), 14)
                self.assertEqual(dialog.preview.font().family(), 'Segoe UI')
                for name in ('bold', 'heading', 'code_block', 'list', 'preview', 'media', 'advanced'):
                    button = dialog.ui.findChild(QPushButton, name)
                    self.assertFalse(button.icon().isNull(), name)
                    self.assertFalse(button.icon().pixmap(18, 18).isNull(), name)
                    self.assertEqual(button.width(), 32)
                    self.assertEqual(button.height(), 32)
                    self.assertTrue(button.toolTip())
