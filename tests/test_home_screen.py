import unittest

from PySide6.QtCore import Qt, QCoreApplication, QEvent
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QWidget, QScrollArea, QBoxLayout

from core.localization.localization import Localization
from core.localization.ui_translator import translate_ui
from core.theme.theme_manager import ThemeManager
from core.ui.home.home_screen import HomeScreen


class HomeScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        stylesheet = self.app.styleSheet()
        self.addCleanup(self.app.setStyleSheet, stylesheet)
        self.themes = ThemeManager(self.app)
        self.themes.apply('dark')
        self.home = HomeScreen()
        self.addCleanup(self.dispose)

    def dispose(self):
        self.home.close()
        self.home.deleteLater()
        QCoreApplication.sendPostedEvents(self.home, QEvent.DeferredDelete)

    def test_mouse_and_keyboard_actions_emit_once(self):
        self.home.resize(900, 600)
        self.home.show()
        self.app.processEvents()
        for name, signal in [('open_snips', self.home.open_snips),
                             ('open_settings', self.home.open_settings)]:
            with self.subTest(action=name):
                calls = []
                signal.connect(lambda: calls.append(True))
                button = self.home.ui.findChild(QPushButton, name)
                self.assertFalse(button.icon().isNull())
                self.assertFalse(button.icon().pixmap(button.iconSize()).isNull())
                QTest.mouseClick(button, Qt.LeftButton)
                self.assertEqual(len(calls), 1)
                button.setFocus()
                QTest.keyClick(button, Qt.Key_Space)
                self.assertEqual(len(calls), 2)
                signal.disconnect()

    def test_live_localization_themes_and_responsive_layout(self):
        self.home.show()
        body = self.home.ui.findChild(QWidget, 'home_body')
        snips = self.home.ui.findChild(QWidget, 'snips_card')
        settings = self.home.ui.findChild(QWidget, 'settings_card')
        fields = [('home_subtitle', 'home.intro', QLabel),
                  ('snips_title', 'nav.snips', QLabel),
                  ('settings_title', 'nav.settings', QLabel),
                  ('snips_description', 'home.snips_description', QLabel),
                  ('settings_description', 'home.settings_description', QLabel),
                  ('open_snips', 'home.open_snips', QPushButton),
                  ('open_settings', 'home.open_settings', QPushButton)]
        for language in ('en', 'he', 'en'):
            localization = Localization(language)
            translate_ui(self.home, localization)
            for theme in ('dark', 'light', 'dark'):
                self.themes.apply(theme)
                for width, height in [(1200, 800), (640, 480), (380, 640), (380, 320)]:
                    with self.subTest(language=language, theme=theme, size=(width, height)):
                        self.home.resize(width, height)
                        # Direction changes propagate through nested scroll layouts.
                        QTest.qWait(20)
                        self.assertEqual(self.home.width(), width)
                        self.assertEqual(self.home.layoutDirection(), Qt.RightToLeft if localization.rtl else Qt.LeftToRight)
                        self.assertLessEqual(body.width(), 700)
                        scroll = self.home.ui.findChild(QScrollArea, 'home_scroll')
                        self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
                        center = body.mapTo(scroll.viewport(), body.rect().center()).x()
                        self.assertLessEqual(abs(center - scroll.viewport().rect().center().x()), 1)
                        if width < 600:
                            self.assertEqual(self.home.cards_layout.direction(), QBoxLayout.TopToBottom)
                            self.assertLess(snips.y(), settings.y())
                            self.assertEqual(snips.width(), settings.width())
                        else:
                            self.assertEqual(snips.x() > settings.x(), localization.rtl)
                            self.assertLessEqual(abs(snips.width() - settings.width()), 1)
                        for name, key, widget_type in fields:
                            widget = self.home.ui.findChild(widget_type, name)
                            self.assertIn(key, localization.strings)
                            self.assertEqual(widget.text(), localization.text(key))
                            if isinstance(widget, QPushButton):
                                self.assertGreaterEqual(widget.width(), widget.sizeHint().width())
                                self.assertFalse(widget.icon().pixmap(widget.iconSize()).isNull())
                            else:
                                self.assertTrue(widget.alignment() & (Qt.AlignHCenter if name == 'home_subtitle' else Qt.AlignLeading))
                                self.assertGreaterEqual(widget.height(), widget.heightForWidth(widget.width()))
                        colors = self.app.property('themeColors')
                        primary = self.home.ui.findChild(QPushButton, 'open_snips')
                        secondary = self.home.ui.findChild(QPushButton, 'open_settings')
                        self.assertEqual(primary.palette().color(QPalette.Button).name().upper(), colors['accent'])
                        self.assertEqual(secondary.palette().color(QPalette.Button).name().upper(), colors['surface'])
                        if height == 320:
                            self.assertGreater(scroll.verticalScrollBar().maximum(), 0)
