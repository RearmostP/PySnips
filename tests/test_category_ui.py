from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from core.localization.localization import Localization
from core.snips.library import SnippetLibrary
from core.ui.snips.snips_screen import SnipsScreen
from core.ui.snips.dialogs.deleted_snippets import DeletedSnippets


class CategoryUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.library = SnippetLibrary(Path(self.temp.name))
        self.localization = Localization('en')
        self.messages = Mock()
        self.messages.confirm.return_value = True
        self.screen = SnipsScreen(self.library, self.localization, self.messages)
        self.addCleanup(self.screen.close)
        self.screen.refresh_categories()

    def button(self, name):
        return next(button for value, button in self.screen.category_buttons if value == name)

    def test_context_menu_pin_unpin_order_and_recent_has_no_actions(self):
        self.assertEqual(self.button(None).contextMenuPolicy(), Qt.DefaultContextMenu)
        button = self.button('PySide6')
        self.assertEqual(button.contextMenuPolicy(), Qt.CustomContextMenu)
        with patch.object(self.screen, 'category_menu') as build_menu:
            button.customContextMenuRequested.emit(QPoint(1, 1))
            build_menu.assert_called_once_with('PySide6', button)
            build_menu.return_value.exec.assert_called_once()
            build_menu.return_value.deleteLater.assert_called_once()
        menu = self.screen.category_menu('PySide6', button)
        self.assertEqual([action.text() for action in menu.actions()], ['Pin', 'Delete category'])
        menu.actions()[0].trigger()
        self.assertEqual([name for name, _ in self.screen.category_buttons], [None, 'PySide6', 'Python'])
        menu = self.screen.category_menu('PySide6', self.button('PySide6'))
        self.assertEqual([action.text() for action in menu.actions()], ['Unpin', 'Delete category'])
        menu.actions()[0].trigger()
        self.assertEqual([name for name, _ in self.screen.category_buttons], [None, 'Python', 'PySide6'])
        self.messages.error_key.assert_not_called()

    def test_delete_confirmation_cancel_and_selected_category_refresh(self):
        self.library.create('Example', 'Python', 'word')
        self.screen.select_category('Python')
        before = self.library.categories_file.read_bytes()
        self.messages.confirm.return_value = False
        menu = self.screen.category_menu('Python', self.button('Python'))
        menu.actions()[1].trigger()
        self.assertEqual(self.library.categories_file.read_bytes(), before)
        self.assertTrue((self.library.root / 'Python').exists())
        self.assertEqual(self.screen.current_category, 'Python')
        self.messages.confirm.assert_called_with(
            self.localization.text('category.confirm_delete', category='Python'))
        self.messages.confirm.return_value = True
        menu.actions()[1].trigger()
        self.assertEqual(self.screen.current_category, None)
        self.assertEqual([name for name, _ in self.screen.category_buttons], [None, 'PySide6'])
        self.assertEqual(self.screen.cards, [])
        self.assertTrue((self.library.category_trash / 'Python').exists())
        self.messages.info.assert_called_once()

    def test_category_errors_are_translated(self):
        self.screen.pin_category('Missing', True)
        self.messages.error_key.assert_called_with('errors.category_missing')
        self.messages.error_key.reset_mock()
        with patch.object(self.library, 'delete_category', side_effect=OSError('denied')):
            self.screen.delete_category('Python')
        self.messages.error_key.assert_called_once_with('errors.io')

    def test_trash_separates_categories_and_snippets_and_restores_both(self):
        snippet = self.library.create('Individual', 'PySide6', 'individual')
        self.library.delete(snippet.id)
        self.library.create('Grouped', 'Python', 'grouped')
        self.library.delete_category('Python')
        dialog = DeletedSnippets(self.library, self.localization, self.messages)
        self.addCleanup(dialog.close)
        self.assertEqual(dialog.category_items.count(), 1)
        self.assertEqual(dialog.items.count(), 1)
        self.assertEqual(dialog.ui.findChild(QLabel, 'categories_heading').text(), 'Deleted categories')
        self.assertEqual(dialog.ui.findChild(QLabel, 'heading').text(), 'Deleted snippets')
        self.assertFalse(dialog.ui.findChild(QPushButton, 'restore_category').isEnabled())
        dialog.category_items.setCurrentRow(0)
        dialog.ui.findChild(QPushButton, 'restore_category').click()
        self.assertEqual(dialog.category_items.count(), 0)
        self.assertEqual(dialog.items.count(), 1)
        self.assertIn('Python', self.library.categories())
        dialog.items.setCurrentRow(0)
        dialog.ui.findChild(QPushButton, 'restore').click()
        self.assertEqual(dialog.items.count(), 0)
        self.assertEqual(len(self.library.list()), 2)
        self.messages.error_key.assert_not_called()

    def test_trash_permanent_confirmation_cancel_then_delete(self):
        self.library.delete_category('Python')
        dialog = DeletedSnippets(self.library, self.localization, self.messages)
        self.addCleanup(dialog.close)
        dialog.category_items.setCurrentRow(0)
        self.messages.confirm.return_value = False
        dialog.ui.findChild(QPushButton, 'permanent_category').click()
        self.assertEqual(dialog.category_items.count(), 1)
        self.assertTrue((self.library.category_trash / 'Python').exists())
        self.messages.confirm.assert_called_with(
            self.localization.text('category.confirm_permanent', category='Python'))
        self.messages.confirm.return_value = True
        dialog.ui.findChild(QPushButton, 'permanent_category').click()
        self.assertEqual(dialog.category_items.count(), 0)
        self.assertFalse((self.library.category_trash / 'Python').exists())

    def test_restore_conflict_keeps_category_visible_in_trash(self):
        self.library.delete_category('Python')
        (self.library.root / 'Python').mkdir()
        dialog = DeletedSnippets(self.library, self.localization, self.messages)
        self.addCleanup(dialog.close)
        dialog.category_items.setCurrentRow(0)
        dialog.restore_category()
        self.messages.error_key.assert_called_once_with('errors.category_destination_exists')
        self.assertEqual(dialog.category_items.count(), 1)

    def test_hebrew_localization_rtl_and_complete_category_keys(self):
        self.localization.set_language('he')
        self.screen.refresh_categories()
        menu = self.screen.category_menu('Python', self.button('Python'))
        self.assertEqual(menu.layoutDirection(), Qt.RightToLeft)
        self.assertEqual([action.text() for action in menu.actions()], ['נעיצה', 'מחיקת קטגוריה'])
        dialog = DeletedSnippets(self.library, self.localization, self.messages)
        self.addCleanup(dialog.close)
        self.assertEqual(dialog.layoutDirection(), Qt.RightToLeft)
        self.assertEqual(dialog.ui.findChild(QLabel, 'categories_heading').text(), 'קטגוריות שנמחקו')
        for key in self.localization.english:
            if key.startswith(('category.', 'trash.', 'errors.category_', 'errors.deleted_category_')):
                self.assertIn(key, self.localization.strings)
                self.assertNotIn('??', self.localization.text(key, category='Python'))
