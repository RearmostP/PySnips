import json
from pathlib import Path
import re
from string import Template
import tempfile
import unittest
from unittest.mock import Mock

from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLineEdit

from core.common.paths import THEMES_DIR
from core.theme.theme_manager import ThemeManager


class ThemeManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.app = Mock()
        self.manager = ThemeManager(self.app, self.directory)
        self.template = 'QWidget { background: $background; color: $text; border-color: $text_muted; }'
        (self.directory / 'style.qss').write_text(self.template, encoding='utf-8')
        self.colors = {'background': '#16171B', 'text': '#E8E8E8', 'text_muted': '#C8C8C8'}
        self.write_theme('dark', self.colors)

    def write_theme(self, name, colors):
        folder = self.directory / name
        folder.mkdir(exist_ok=True)
        (folder / 'colors.json').write_text(json.dumps(colors), encoding='utf-8')

    def test_discovery_uses_palettes_and_ignores_old_stylesheets(self):
        self.write_theme('light', self.colors)
        (self.directory / 'legacy').mkdir()
        (self.directory / 'legacy' / 'style.qss').write_text('', encoding='utf-8')
        self.assertEqual(self.manager.available_themes(), ['dark', 'light'])

    def test_replacement_handles_repetition_and_prefixes(self):
        (self.directory / 'style.qss').write_text(
            self.template + '\nQLabel { color: ${text}; background: $background; }', encoding='utf-8')
        self.manager.apply('dark')
        applied = self.app.setStyleSheet.call_args.args[0]
        self.assertNotIn('$', applied)
        self.assertEqual(applied.count('#16171B'), 2)
        self.assertEqual(applied.count('#E8E8E8'), 2)
        self.assertIn('border-color: #C8C8C8', applied)

    def test_switching_reloads_the_selected_palette(self):
        self.write_theme('light', dict(self.colors, background='#ECEEF1'))
        for name, color in [('dark', '#16171B'), ('light', '#ECEEF1'), ('dark', '#16171B')]:
            self.manager.apply(name)
            self.assertEqual(self.manager.current, name)
            self.assertIn(color, self.app.setStyleSheet.call_args.args[0])

    def test_unknown_or_missing_theme_falls_back_to_dark(self):
        for name in ['unknown', '../outside', 'light']:
            self.manager.apply(name)
            self.assertEqual(self.manager.current, 'dark')
            self.assertIn('#16171B', self.app.setStyleSheet.call_args.args[0])

    def test_missing_color_preserves_the_active_theme(self):
        self.manager.apply('dark')
        self.write_theme('light', {'background': '#ECEEF1'})
        with self.assertRaisesRegex(ValueError, 'Missing colors: text, text_muted'):
            self.manager.apply('light')
        self.assertEqual(self.manager.current, 'dark')
        self.assertEqual(self.app.setStyleSheet.call_count, 1)

    def test_invalid_palettes_fail_before_application(self):
        for colors in [[], None, {'text': 123}, {'text': 'red; border: none'}, {'text': '#GGGGGG'}]:
            with self.subTest(colors=colors):
                self.write_theme('light', colors)
                with self.assertRaisesRegex(ValueError, "Cannot load theme 'light'"):
                    self.manager.apply('light')
        self.app.setStyleSheet.assert_not_called()

    def test_malformed_json_and_duplicate_keys_fail_clearly(self):
        self.write_theme('light', self.colors)
        for content in ['{', '{"text": "#FFFFFF", "text": "#000000"}']:
            (self.directory / 'light' / 'colors.json').write_text(content, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, "Cannot load theme 'light'"):
                self.manager.apply('light')
        self.app.setStyleSheet.assert_not_called()

    def test_missing_template_or_default_palette_fails_clearly(self):
        (self.directory / 'style.qss').unlink()
        with self.assertRaisesRegex(ValueError, 'style.qss'):
            self.manager.apply('dark')
        (self.directory / 'dark' / 'colors.json').unlink()
        with self.assertRaisesRegex(ValueError, 'colors.json'):
            self.manager.apply('unknown')
        self.app.setStyleSheet.assert_not_called()

    def test_invalid_placeholder_is_rejected(self):
        (self.directory / 'style.qss').write_text('QWidget { color: $; }', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Invalid color placeholder'):
            self.manager.apply('dark')
        self.app.setStyleSheet.assert_not_called()

    def test_transparent_colors_are_supported(self):
        self.write_theme('dark', dict(self.colors, background='transparent'))
        self.manager.apply('dark')
        self.assertIn('background: transparent;', self.app.setStyleSheet.call_args.args[0])

    def test_shared_stylesheet_has_unique_selectors_and_semantic_properties(self):
        stylesheet = (THEMES_DIR / 'style.qss').read_text(encoding='utf-8')
        stylesheet = re.sub(r'/\*.*?\*/', '', stylesheet, flags=re.S)
        selectors = [selector.strip() for group in re.findall(r'([^{}]+)\{', stylesheet)
                     for selector in group.split(',')]
        self.assertEqual(len(selectors), len(set(selectors)))
        for selector in [
            'QPlainTextEdit[codeEditor="true"]',
            'QWidget#CreateSnippetForm QPushButton[toolbarAction="true"]:focus',
            'QWidget#SnippetDetails QLabel[metadataLabel="true"]',
            'QWidget#SnippetCardWidget QLabel[tagBadge="true"]',
            'QWidget#SnippetsScreen QPushButton[categoryNav="true"]:checked:hover',
            'QWidget#SnippetsScreen QPushButton[categoryNav="true"][navRtl="true"]',
            'QWidget#SettingsScreen QCheckBox[settingsControl="true"]::indicator:checked',
            'QWidget#AboutForm QPushButton[aboutLink="true"]:hover',
            'QWidget#SnippetCardWidget QPushButton#delete:disabled',
        ]:
            self.assertIn(selector, selectors)

    def test_bundled_palettes_cover_exactly_the_shared_placeholders(self):
        stylesheet = (THEMES_DIR / 'style.qss').read_text(encoding='utf-8')
        self.assertNotRegex(stylesheet, r'#[0-9a-fA-F]{3,8}\b')
        identifiers = set(Template(stylesheet).get_identifiers())
        for theme in ['dark', 'light']:
            colors = json.loads((THEMES_DIR / theme / 'colors.json').read_text(encoding='utf-8'))
            self.assertEqual(identifiers, set(colors), theme)
            manager = ThemeManager(self.app)
            manager.apply(theme)
            self.assertNotIn('$', self.app.setStyleSheet.call_args.args[0])


class ThemeQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_existing_widgets_restyle_in_both_directions_without_qss_errors(self):
        previous_stylesheet = self.app.styleSheet()
        self.addCleanup(self.app.setStyleSheet, previous_stylesheet)
        window = QWidget()
        button = QPushButton('Test', window)
        field = QLineEdit(window)
        self.addCleanup(window.close)
        messages = []
        previous_handler = qInstallMessageHandler(lambda kind, context, message: messages.append(message))
        try:
            manager = ThemeManager(self.app)
            for theme in ['dark', 'light', 'dark']:
                manager.apply(theme)
                window.show()
                self.app.processEvents()
                colors = json.loads((THEMES_DIR / theme / 'colors.json').read_text(encoding='utf-8'))
                self.assertEqual(window.palette().color(QPalette.Window).name().upper(), colors['background'])
                self.assertEqual(field.palette().color(QPalette.Base).name().upper(), colors['input_background'])
                self.assertEqual(button.palette().color(QPalette.Button).name().upper(), colors['surface'])
            self.assertFalse([m for m in messages if 'stylesheet' in m.lower() or 'unknown property' in m.lower()], messages)
        finally:
            qInstallMessageHandler(previous_handler)
