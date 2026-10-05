from math import ceil
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextBrowser
from core.localization.ui_translator import translate_ui
from core.markdown.renderer import render_markdown


class SnippetCard(QWidget):
    details_requested = Signal(str)
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, snippet, media_base, localization, parent=None):
        super().__init__(parent)
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        self.title = self.ui.findChild(QLabel, 'title')
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.title.setText(snippet.title)
        self.preview = self.ui.findChild(QTextBrowser, 'content')
        self.snippet = snippet
        self.localization = localization
        self.preview.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.preview.customContextMenuRequested.connect(self.show_context_menu)
        for name, signal in [('details', self.details_requested),
                             ('edit', self.edit_requested), ('delete', self.delete_requested)]:
            self.ui.findChild(QPushButton, name).clicked.connect(
                lambda checked=False, event=signal: event.emit(snippet.id))
        translate_ui(self, localization)
        render_markdown(self.preview, snippet.content, media_base)
        self._height_pending = False
        self.preview.document().documentLayout().documentSizeChanged.connect(self.schedule_height)
        self.schedule_height()

    def schedule_height(self, *args):
        if not self._height_pending:
            self._height_pending = True
            QTimer.singleShot(0, self.update_height)

    def update_height(self):
        self._height_pending = False
        # Same content-aware 170..600px card bounds as the reference.
        document_height = ceil(self.preview.document().size().height())
        layout = self.ui.layout()
        margins = layout.contentsMargins()
        header = (margins.top() + margins.bottom() + self.title.sizeHint().height()
                  + self.ui.findChild(QPushButton, 'details').height() + layout.spacing() * 2)
        self.setFixedHeight(max(170, min(600, header + document_height + 12)))

    def show_context_menu(self, position):
        from PySide6.QtWidgets import QApplication
        menu = self.preview.createStandardContextMenu()
        menu.addSeparator()
        menu.addAction(self.localization.text('snips.copy'),
                       lambda: QApplication.clipboard().setText(self.snippet.content))
        menu.exec(self.preview.mapToGlobal(position))
        menu.deleteLater()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_height_pending'):
            self.schedule_height()
