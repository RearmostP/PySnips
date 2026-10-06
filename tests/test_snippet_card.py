from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt, QPoint, QUrl, QCoreApplication, QEvent
from PySide6.QtGui import QImage, QColor, QTextDocument
from PySide6.QtWidgets import QApplication, QPushButton, QGridLayout

from core.localization.localization import Localization
from core.localization.ui_translator import translate_ui
from core.snips.library import SnippetLibrary
from core.theme.theme_manager import ThemeManager
from core.ui.snips.widgets.snippet_card import SnippetCard


class SnippetCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.library = SnippetLibrary(Path(self.temp.name))
        self.localization = Localization('en')
        self.themes = ThemeManager(self.app)
        self.themes.apply('dark')

    def card(self, title='Example', content='Short preview', tags=''):
        snippet = self.library.create(title, 'Python', content, tags)
        card = SnippetCard(snippet, Path(self.temp.name), self.localization)
        card.resize(480, 170)
        card.show()
        self.addCleanup(self.dispose, card)
        self.settle()
        return card

    def dispose(self, card):
        card.close()
        card.deleteLater()
        QCoreApplication.sendPostedEvents(card, QEvent.Type.DeferredDelete)

    def settle(self):
        for _ in range(8):
            self.app.processEvents()

    def test_separate_title_and_action_row_preserve_snippet_id(self):
        card = self.card('<b>Literal title</b>', tags='git, branch')
        self.assertEqual(card.title.textFormat(), Qt.TextFormat.PlainText)
        for language in ('en', 'he'):
            self.localization.set_language(language)
            translate_ui(card, self.localization)
            self.settle()
            details = card.ui.findChild(QPushButton, 'details')
            title_y = card.title.mapTo(card, card.title.rect().center()).y()
            button_y = details.mapTo(card, details.rect().center()).y()
            self.assertLess(title_y, button_y)
            edit = card.ui.findChild(QPushButton, 'edit')
            delete = card.ui.findChild(QPushButton, 'delete')
            self.assertLess(details.mapTo(card, details.rect().center()).x(),
                            edit.mapTo(card, edit.rect().center()).x())
            self.assertLess(edit.mapTo(card, edit.rect().center()).x(),
                            delete.mapTo(card, delete.rect().center()).x())
            self.assertEqual(card.preview.layoutDirection(), Qt.LayoutDirection.LeftToRight)
            buttons = [card.ui.findChild(QPushButton, name) for name in ('details', 'edit', 'delete')]
            self.assertEqual({button.height() for button in buttons}, {35})
            for name, signal in [('details', card.details_requested),
                                 ('edit', card.edit_requested), ('delete', card.delete_requested)]:
                received = []
                signal.connect(received.append)
                card.ui.findChild(QPushButton, name).click()
                self.assertEqual(received, [card.snippet.id])
                signal.disconnect(received.append)

    def test_tags_are_optional_plain_text_and_bounded(self):
        empty = self.card()
        self.assertTrue(empty.tags.isHidden())
        long_tag = '<b>developer-tag</b>' * 8
        tagged = self.card(tags=['git', 'branch', long_tag, 'qt'])
        badges = tagged.tags.findChild(QGridLayout, 'tagsLayout')
        self.assertEqual(badges.count(), 4)
        badge = badges.itemAt(2).widget()
        self.assertEqual(badge.textFormat(), Qt.TextFormat.PlainText)
        self.assertEqual(badge.toolTip(), long_tag)
        self.assertLess(len(badge.text()), len(long_tag))
        self.assertEqual(self.library.load(tagged.snippet.id).tags, tagged.snippet.tags)
        tagged.resize(340, tagged.height())
        self.settle()
        self.assertEqual(tagged.width(), 340)
        self.assertLessEqual(tagged.tags.width(), 316)

    def test_height_tracks_content_width_and_theme(self):
        short = self.card()
        medium = self.card(content='\n\n'.join(['A readable paragraph with a few words.'] * 8))
        tall = self.card(content='\n\n'.join(['Paragraph'] * 100))
        self.assertGreater(medium.height(), short.height())
        self.assertEqual(tall.height(), 600)
        for theme in ('light', 'dark'):
            self.themes.apply(theme)
            self.settle()
            self.assertEqual(short.title.font().pixelSize(), 14)
            self.assertEqual(short.title.font().family(), 'Segoe UI')
            for width in (480, 340, 700):
                medium.resize(width, medium.height())
                self.settle()
                self.assertGreaterEqual(medium.height(), 170)
                self.assertLessEqual(medium.height(), 600)
                self.assertLessEqual(medium.header.width(), width)
                self.assertEqual(medium.preview.verticalScrollBar().maximum(), 0)

    def test_markdown_media_and_context_copy_are_preserved(self):
        image = QImage(32, 24, QImage.Format.Format_RGB32)
        image.fill(QColor('red'))
        image.save(str(Path(self.temp.name) / 'example.png'))
        markdown = '**Bold prose**\n\n```python\nprint(123)\n```\n\n![example](example.png)'
        card = self.card(content=markdown)
        self.assertIn('Bold prose', card.preview.toPlainText())
        self.assertIn('print(123)', card.preview.toPlainText())
        self.assertIn('JetBrains Mono', card.preview.document().defaultStyleSheet())
        resource = card.preview.document().resource(QTextDocument.ResourceType.ImageResource, QUrl('example.png'))
        self.assertIsNotNone(resource)
        self.assertFalse(resource.isNull())
        menu = card.preview.createStandardContextMenu()
        with patch.object(card.preview, 'createStandardContextMenu', return_value=menu):
            with patch.object(menu, 'exec', side_effect=lambda *_: menu.actions()[-1].trigger()):
                card.show_context_menu(QPoint(0, 0))
        self.assertEqual(self.app.clipboard().text(), markdown)
