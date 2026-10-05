from pathlib import Path
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QGridLayout, QSizePolicy, QWidget
from core.localization.ui_translator import translate_ui
from core.snips.models import LibraryError
from core.ui.snips.dialogs.create_snippet import CreateSnippet


class SnippetDetails(QDialog):
    def __init__(self, library, localization, messages, snippet, parent=None):
        super().__init__(parent)
        self.library, self.localization, self.messages, self.snippet = library, localization, messages, snippet
        self.setProperty('i18nTitleKey', 'snips.details_title')
        self.resize(420, 256)
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        self.setWindowTitle(self.ui.windowTitle())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        for label in self.ui.findChildren(QLabel):
            label.setTextFormat(Qt.TextFormat.PlainText)
        self.ui.findChild(QPushButton, 'edit').clicked.connect(self.edit)
        self.ui.findChild(QPushButton, 'close').clicked.connect(self.accept)
        translate_ui(self, localization)
        self.refresh()

    def refresh(self):
        self.ui.findChild(QLabel, 'title').setText(self.snippet.title)
        tags_layout = self.ui.findChild(QGridLayout, 'tagsLayout')
        tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignTop)
        while tags_layout.count():
            item = tags_layout.takeAt(0)
            item.widget().hide()
            item.widget().deleteLater()
        for index, tag in enumerate(self.snippet.tags or ['—']):
            badge = QLabel(tag)
            badge.setTextFormat(Qt.TextFormat.PlainText)
            badge.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            badge.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
            badge.setProperty('tagBadge', bool(self.snippet.tags))
            tags_layout.addWidget(badge, index // 3, index % 3)
            badge.ensurePolished()
            badge.setText(badge.fontMetrics().elidedText(tag, Qt.TextElideMode.ElideRight, 100))
            badge.setToolTip(tag)
            badge.show()
        try:
            created = datetime.fromisoformat(self.snippet.created_at).astimezone()
            created_text = created.strftime('%d/%m/%Y %H:%M')
        except (ValueError, TypeError, OverflowError):
            created_text = '—'
        self.ui.findChild(QLabel, 'created_at').setText(created_text)
        self.ui.findChild(QLabel, 'category').setText(self.snippet.category)
        tags_layout.parentWidget().updateGeometry()
        self.ui.findChild(QWidget, 'metadataPanel').updateGeometry()
        self.ui.updateGeometry()
        self.layout().activate()
        height = self.layout().totalHeightForWidth(self.width())
        self.resize(self.width(), height if height >= 0 else self.sizeHint().height())

    def edit(self):
        try:
            dialog = CreateSnippet(self.library, self.localization, self.messages, self.snippet, self)
            if dialog.exec():
                self.snippet = dialog.snippet
                self.refresh()
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))
