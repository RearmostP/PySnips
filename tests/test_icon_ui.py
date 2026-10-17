from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QPushButton

from core.localization.localization import Localization
from core.localization.ui_translator import translate_ui
from core.settings.settings import Settings
from core.snips.library import SnippetLibrary
from core.theme.theme_manager import ThemeManager
from core.ui.main_window import MainWindow
from core.ui.dialogs.cloud_backup import CloudBackupDialog
from core.ui.snips.dialogs.create_snippet import CreateSnippet
from core.ui.snips.dialogs.deleted_snippets import DeletedSnippets
from core.ui.snips.dialogs.snippet_details import SnippetDetails


def shape(icon):
    image = icon.pixmap(24, 24).toImage()
    return [[image.pixelColor(x, y).alpha() > 127 for x in range(image.width())]
            for y in range(image.height())]


class IconUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        launcher = patch('core.common.update_process.UpdaterProcess.launch')
        launcher.start()
        self.addCleanup(launcher.stop)
        self.library = SnippetLibrary(Path(self.temp.name))
        self.snippet = self.library.create('Example', 'Python', 'example content')
        self.localization = Localization('en')
        self.themes = ThemeManager(self.app)
        self.themes.apply('dark')
        self.window = MainWindow(self.library, Settings('en'), self.localization, self.themes)
        self.addCleanup(self.dispose, self.window)
        self.window.show_snips()
        self.app.processEvents()

    def dispose(self, widget):
        self.app.processEvents()
        widget.close()
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(widget, QEvent.DeferredDelete)

    def assert_button_icons(self, root, names):
        for name in names:
            with self.subTest(button=name):
                button = root.findChild(QPushButton, name)
                self.assertIsNotNone(button)
                self.assertFalse(button.icon().isNull())
                self.assertFalse(button.icon().pixmap(button.iconSize()).isNull())

    def test_home_snips_cards_and_settings_keep_text_and_have_icons(self):
        self.assert_button_icons(self.window.home.ui, ('open_snips', 'open_settings'))
        self.assert_button_icons(self.window.snips.ui, ('menu', 'add_category', 'create'))
        self.assert_button_icons(self.window.snips.cards[0].ui, ('details', 'edit', 'delete'))
        self.assert_button_icons(self.window.settings_screen.ui,
                                 ('back', 'deleted', 'cloud_manage', 'about', 'check_updates'))
        self.assertEqual(self.window.home.ui.findChild(QPushButton, 'open_snips').text(),
                         self.localization.text('nav.snips'))
        menu_button = self.window.snips.ui.findChild(QPushButton, 'menu')
        self.assertEqual(menu_button.text(), '')
        self.assertEqual(menu_button.toolTip(), self.localization.text('snips.menu'))
        self.assertEqual(menu_button.accessibleName(), menu_button.toolTip())
        for action in self.window.snips.menu.actions():
            self.assertFalse(action.icon().isNull())
        self.assertFalse(self.window.snips.search.search_icon.icon().isNull())
        self.assertFalse(self.window.snips.search.search_icon.isEnabled())

    def test_category_menu_and_pinning_change_category_glyph(self):
        screen = self.window.snips
        button = next(button for name, button in screen.category_buttons if name == 'Python')
        original = shape(button.icon())
        menu = screen.category_menu('Python', button)
        self.assertEqual(len(menu.actions()), 2)
        self.assertTrue(all(not action.icon().isNull() for action in menu.actions()))
        menu.actions()[0].trigger()
        pinned = next(button for name, button in screen.category_buttons if name == 'Python')
        self.assertNotEqual(original, shape(pinned.icon()))
        unpin = screen.category_menu('Python', pinned)
        self.assertEqual(unpin.actions()[0].text(), self.localization.text('category.unpin'))
        self.assertFalse(unpin.actions()[0].icon().isNull())
        self.assertNotEqual(shape(menu.actions()[0].icon()), shape(unpin.actions()[0].icon()))

    def test_editor_and_details_buttons_and_toolbar_accessibility(self):
        dialog = CreateSnippet(self.library, self.localization, self.window.messages)
        self.addCleanup(self.dispose, dialog)
        self.assert_button_icons(dialog.ui, ('save', 'cancel', 'bold', 'heading', 'code_block',
                                             'list', 'preview', 'media', 'advanced'))
        for name in ('bold', 'heading', 'code_block', 'list', 'preview', 'media', 'advanced'):
            button = dialog.ui.findChild(QPushButton, name)
            self.assertEqual(button.text(), '')
            self.assertTrue(button.toolTip())
            self.assertEqual(button.accessibleName(), button.toolTip())
        details = SnippetDetails(self.library, self.localization, self.window.messages, self.snippet)
        self.addCleanup(self.dispose, details)
        self.assert_button_icons(details.ui, ('edit', 'close'))

    def test_trash_and_cloud_actions_have_icons_without_changing_behavior(self):
        trash = DeletedSnippets(self.library, self.localization, self.window.messages)
        self.addCleanup(self.dispose, trash)
        self.assert_button_icons(trash.ui, ('restore', 'restore_category', 'permanent',
                                           'permanent_category', 'close'))
        provider = Mock()
        provider.connected = False
        with patch.object(CloudBackupDialog, 'resume'):
            cloud = CloudBackupDialog(self.library, self.localization, self.window.messages, provider=provider)
            self.app.processEvents()  # Consume the deferred startup while resume is mocked.
        self.addCleanup(self.dispose, cloud)
        for button in (cloud.connect_button, cloud.disconnect_button, cloud.backup_button, cloud.restore_button):
            self.assertFalse(button.icon().isNull())
            self.assertTrue(button.text())
        self.assertFalse(cloud.restore_button.isEnabled())
        provider.connect.assert_not_called()
        provider.upload.assert_not_called()

    def test_settings_back_arrow_follows_live_language_switch(self):
        back = self.window.settings_screen.ui.findChild(QPushButton, 'back')
        original = shape(back.icon())
        self.localization.set_language('he')
        self.window.settings_screen.retranslate(Settings('he'))
        self.assertEqual(back.layoutDirection(), Qt.RightToLeft)
        self.assertEqual(shape(back.icon()), [row[::-1] for row in original])
        self.assertEqual(back.text(), self.localization.text('common.back'))
        self.localization.set_language('en')
        self.window.settings_screen.retranslate(Settings('en'))
        self.assertEqual(shape(back.icon()), original)

    def test_button_icon_placement_and_search_follow_hebrew_in_ltr_containers(self):
        self.localization.set_language('he')
        translate_ui(self.window, self.localization)
        self.window.snips.refresh()
        for root, name in ((self.window.home.ui, 'open_snips'),
                           (self.window.snips.ui, 'create'),
                           (self.window.snips.cards[0].ui, 'delete')):
            self.assertEqual(root.findChild(QPushButton, name).layoutDirection(), Qt.RightToLeft)
        self.assertEqual(self.window.snips.search.query.layoutDirection(), Qt.RightToLeft)

    def test_card_buttons_can_fit_icons_and_translated_labels(self):
        self.window.show()
        for language in ('en', 'he'):
            self.localization.set_language(language)
            translate_ui(self.window, self.localization)
            for theme in ('dark', 'light'):
                self.themes.apply(theme)
                self.app.processEvents()
                for name in ('details', 'edit', 'delete'):
                    button = self.window.snips.cards[0].ui.findChild(QPushButton, name)
                    self.assertGreaterEqual(button.width(), button.sizeHint().width())
                    self.assertEqual(button.height(), 35)
                    self.assertGreaterEqual(button.parentWidget().height(), button.height())
