from math import ceil
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QTextBrowser, QSizePolicy
from core.localization.ui_translator import translate_ui
from core.markdown.renderer import render_markdown


MINIMUM_CARD_HEIGHT = 170
CONTENT_HEIGHT_PADDING = 12
DEFAULT_MAXIMUM_CARD_HEIGHT = 600


class SnippetCard(QWidget):
    details_requested = Signal(str)
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, snippet, media_base, localization, parent=None, *, card_height=DEFAULT_MAXIMUM_CARD_HEIGHT):
        super().__init__(parent)
        self._maximum_card_height = max(300, min(int(card_height), 900))
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
        self.header = self.ui.findChild(QWidget, 'cardHeader')
        self.tags = self.ui.findChild(QWidget, 'cardTags')
        tags_layout = self.tags.findChild(QGridLayout, 'tagsLayout')
        tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignTop)
        for index, tag in enumerate(snippet.tags):
            badge = QLabel(self.tags)
            badge.setTextFormat(Qt.TextFormat.PlainText)
            badge.setProperty('tagBadge', True)
            badge.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
            badge.setToolTip(tag)
            tags_layout.addWidget(badge, index // 3, index % 3)
            badge.ensurePolished()
            badge.setText(badge.fontMetrics().elidedText(tag, Qt.TextElideMode.ElideRight, 80))
        self.tags.setVisible(bool(snippet.tags))
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
        # Original content-aware sizing, plus the current optional tag row.
        document_height = ceil(self.preview.document().size().height())
        layout = self.ui.layout()
        margins = layout.contentsMargins()
        actions = self.ui.findChild(QWidget, 'cardActions').layout()
        header_height = self.title.sizeHint().height() + actions.sizeHint().height()
        tags_height = 0 if self.tags.isHidden() else self.tags.sizeHint().height() + layout.spacing()
        preview_chrome = self.preview.frameWidth() * 2 + CONTENT_HEIGHT_PADDING
        height = (margins.top() + margins.bottom() + header_height + tags_height
                  + layout.spacing() * 2 + document_height + preview_chrome)
        self.setFixedHeight(max(MINIMUM_CARD_HEIGHT, min(self._maximum_card_height, height)))

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
