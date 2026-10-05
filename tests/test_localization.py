from pathlib import Path
import tempfile
import unittest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLineEdit
from core.localization.localization import Localization, parse_language
from core.localization.ui_translator import translate_ui
from core.settings.settings import Settings, load_settings, save_settings


class LocalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_utf8_comments_and_equals(self):
        self.assertEqual(parse_language('# comment\n\n a = שלום = עולם\nbad line\nempty = '), {'a': 'שלום = עולם'})

    def test_missing_key_restores_english_after_language_switch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'en.lang').write_text('button = English', encoding='utf-8')
            (path / 'he.lang').write_text('button = עברית', encoding='utf-8')
            (path / 'partial.lang').write_text('another = something', encoding='utf-8')
            localization = Localization('he', path)
            root = QWidget()
            button = QPushButton('Designer English', root)
            button.setProperty('i18nKey', 'button')
            code = QLineEdit(root)
            code.setProperty('codeEditor', True)
            translate_ui(root, localization)
            self.assertEqual(button.text(), 'עברית')
            self.assertEqual(root.layoutDirection(), Qt.LayoutDirection.RightToLeft)
            self.assertEqual(code.layoutDirection(), Qt.LayoutDirection.LeftToRight)
            localization.set_language('partial')
            translate_ui(root, localization)
            self.assertEqual(button.text(), 'Designer English')
            self.assertEqual(root.layoutDirection(), Qt.LayoutDirection.LeftToRight)

    def test_missing_language_falls_back(self):
        self.assertEqual(Localization('unavailable').language, 'en')

    def test_settings_defaults_do_not_create_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            self.assertEqual(load_settings(path), Settings())
            self.assertFalse(path.exists())
            save_settings(Settings('he', 'light', True), path)
            self.assertEqual(load_settings(path), Settings('he', 'light', True))
