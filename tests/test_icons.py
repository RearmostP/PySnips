from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent, QSize, Qt
from PySide6.QtGui import QIcon, QPalette
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from core.common.paths import ASSETS_DIR
from core.theme.theme_manager import ThemeManager
from core.ui.icons import icon, set_button_icon, ICON_SIZE, NAV_ICON_SIZE


def opaque_colors(image):
    return {image.pixelColor(x, y).name()
            for x in range(image.width()) for y in range(image.height())
            if image.pixelColor(x, y).alpha() > 250}


def silhouette(image):
    return [[image.pixelColor(x, y).alpha() > 127 for x in range(image.width())]
            for y in range(image.height())]


class IconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.original_stylesheet = self.app.styleSheet()
        self.original_colors = self.app.property('themeColors')
        self.addCleanup(self.app.setStyleSheet, self.original_stylesheet)
        self.addCleanup(self.app.setProperty, 'themeColors', self.original_colors)
        self.button = QPushButton('Test')
        self.addCleanup(self.button.close)

    def test_logical_name_suffix_and_application_logo(self):
        for name in ('actions/delete', 'actions/delete.svg', 'navigation/settings', 'branding/pysnips-multisize.ico'):
            with self.subTest(name=name):
                result = icon(name, self.button)
                self.assertIsInstance(result, QIcon)
                self.assertFalse(result.isNull())
                self.assertFalse(result.pixmap(24, 24).isNull())
        self.assertEqual(silhouette(icon('actions/delete').pixmap(24, 24).toImage()),
                         silhouette(icon('actions/delete.svg').pixmap(24, 24).toImage()))

    def test_paths_resolve_from_assets_not_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'icons/actions').mkdir(parents=True)
            svg = (ASSETS_DIR / 'icons/actions/add.svg').read_bytes()
            (root / 'icons/actions/example.svg').write_bytes(svg)
            with patch('core.ui.icons.ASSETS_DIR', root):
                self.assertFalse(icon('actions/example').isNull())
                self.assertTrue(icon('actions/delete').isNull())

    def test_missing_invalid_and_unsafe_names_return_empty_icon(self):
        for name in ('missing', '../outside', '/absolute', 'actions/../../outside',
                     'actions\\delete', 'actions/delete.png', '', None):
            with self.subTest(name=name):
                self.assertTrue(icon(name).isNull())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'icons').mkdir()
            (root / 'icons/broken.svg').write_bytes(b'<svg')
            with patch('core.ui.icons.ASSETS_DIR', root):
                self.assertTrue(icon('broken').isNull())
        with patch.object(Path, 'read_bytes', side_effect=OSError('denied')):
            self.assertTrue(icon('actions/add').isNull())

    def test_every_supplied_svg_renders_nonempty_pixels(self):
        self.assertEqual(sum(len(list((ASSETS_DIR / 'icons' / folder).glob('*.svg')))
                             for folder in ('actions', 'navigation', 'content', 'cloud')), 25)
        for folder in ('actions', 'navigation', 'content', 'cloud'):
            for path in (ASSETS_DIR / 'icons' / folder).glob('*.svg'):
                with self.subTest(path=path):
                    name = path.relative_to(ASSETS_DIR / 'icons').as_posix()
                    self.assertIn(b'currentColor', path.read_bytes())
                    self.assertTrue(opaque_colors(icon(name, self.button).pixmap(24, 24).toImage()))

    def test_same_icon_tracks_live_qss_palette_and_disabled_color(self):
        result = icon('actions/delete', self.button)
        themes = ThemeManager(self.app)
        for name, expected in (('dark', '#e8e8e8'), ('light', '#202124'), ('dark', '#e8e8e8')):
            themes.apply(name)
            self.button.ensurePolished()
            self.assertEqual(opaque_colors(result.pixmap(24, 24).toImage()), {expected})
            self.button.setEnabled(False)
            disabled = self.button.palette().color(QPalette.Disabled, self.button.foregroundRole()).name()
            self.assertEqual(opaque_colors(result.pixmap(24, 24, QIcon.Disabled).toImage()), {disabled})
            self.button.setEnabled(True)

    def test_qss_action_foreground_overrides_default_theme_text(self):
        themes = ThemeManager(self.app)
        form = QWidget()
        form.setObjectName('CreateSnippetForm')
        save = QPushButton('Save', form)
        save.setObjectName('save')
        self.addCleanup(form.close)
        result = icon('actions/save', save)
        for theme, expected in (('dark', '#16171b'), ('light', '#f7f8fa')):
            themes.apply(theme)
            save.ensurePolished()
            self.assertEqual(opaque_colors(result.pixmap(24, 24).toImage()), {expected})

    def test_ownerless_icons_use_theme_fallback_and_survive_owner_deletion(self):
        owner = QPushButton()
        orphan = icon('actions/add', owner)
        owner.deleteLater()
        QCoreApplication.sendPostedEvents(owner, QEvent.DeferredDelete)
        standalone = icon('actions/add')
        for theme, expected in (('dark', '#e8e8e8'), ('light', '#202124')):
            ThemeManager(self.app).apply(theme)
            for result in (standalone, orphan):
                self.assertEqual(opaque_colors(result.pixmap(24, 24).toImage()), {expected})

    def test_back_arrow_mirrors_live_direction_other_icons_do_not(self):
        back = icon('navigation/arrow_back', self.button, mirror_rtl=True)
        save = icon('actions/save', self.button)
        self.button.setLayoutDirection(Qt.LeftToRight)
        ltr = silhouette(back.pixmap(24, 24).toImage())
        original_save = silhouette(save.pixmap(24, 24).toImage())
        self.button.setLayoutDirection(Qt.RightToLeft)
        rtl = silhouette(back.pixmap(24, 24).toImage())
        self.assertNotEqual(ltr, rtl)
        self.assertEqual([row[::-1] for row in ltr], rtl)
        self.assertEqual(silhouette(save.pixmap(24, 24).toImage()), original_save)

    def test_high_dpi_and_consistent_button_sizes(self):
        set_button_icon(self.button, 'actions/add')
        self.assertEqual(self.button.iconSize(), QSize(ICON_SIZE, ICON_SIZE))
        for scale in (1.0, 1.25, 1.5, 2.0):
            size = QSize(ICON_SIZE, ICON_SIZE)
            pixmap = self.button.icon().pixmap(size, scale)
            self.assertEqual(pixmap.size(), size * scale)
            self.assertAlmostEqual(pixmap.devicePixelRatio(), scale, delta=.05)
            self.assertTrue(any(any(row) for row in silhouette(pixmap.toImage())))
        set_button_icon(self.button, 'navigation/menu', size=NAV_ICON_SIZE)
        self.assertEqual(self.button.iconSize(), QSize(NAV_ICON_SIZE, NAV_ICON_SIZE))
