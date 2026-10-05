from pathlib import Path
import tempfile
import unittest
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImage, QTextDocument
from PySide6.QtWidgets import QApplication, QTextBrowser
from core.markdown.processor import to_html
from core.markdown.renderer import render_markdown


class MarkdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_highlighted_code_is_ltr_and_escaped(self):
        html = to_html('```python\nprint("<example>")\n```')
        self.assertIn('dir="ltr"', html)
        self.assertIn('span', html)
        self.assertIn('&lt;example&gt;', html)

    def test_unknown_language_keeps_code(self):
        self.assertIn('example', to_html('```unknown-language\nexample\n```'))

    def test_relative_image_loads_from_snippet_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'media').mkdir()
            image = QImage(10, 10, QImage.Format.Format_RGB32)
            image.fill(Qt.GlobalColor.red)
            image.save(str(base / 'media' / 'image.png'))
            browser = QTextBrowser()
            render_markdown(browser, '![Example](media/image.png)', base)
            loaded = browser.document().resource(QTextDocument.ResourceType.ImageResource, QUrl('media/image.png'))
            self.assertIsNotNone(loaded)
            self.assertFalse(loaded.isNull())
            self.assertEqual(loaded.size(), image.size())
