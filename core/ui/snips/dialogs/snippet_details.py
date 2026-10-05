from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from core.localization.ui_translator import translate_ui
from core.snips.models import LibraryError
from core.ui.snips.dialogs.create_snippet import CreateSnippet


class SnippetDetails(QDialog):
    def __init__(self, library, localization, messages, snippet, parent=None):
        super().__init__(parent)
        self.library, self.localization, self.messages, self.snippet = library, localization, messages, snippet
        self.setWindowTitle(snippet.title)
        self.resize(460, 220)
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        QVBoxLayout(self).addWidget(self.ui)
        for label in self.ui.findChildren(QLabel):
            label.setTextFormat(Qt.TextFormat.PlainText)
        self.ui.findChild(QPushButton, 'edit').clicked.connect(self.edit)
        self.ui.findChild(QPushButton, 'close').clicked.connect(self.accept)
        translate_ui(self, localization)
        self.refresh()

    def refresh(self):
        self.ui.findChild(QLabel, 'title').setText(self.snippet.title)
        self.ui.findChild(QLabel, 'tags').setText(', '.join(self.snippet.tags))
        self.ui.findChild(QLabel, 'created_at').setText(self.snippet.created_at)
        self.ui.findChild(QLabel, 'category').setText(self.snippet.category)

    def edit(self):
        try:
            dialog = CreateSnippet(self.library, self.localization, self.messages, self.snippet, self)
            if dialog.exec():
                self.snippet = dialog.snippet
                self.refresh()
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))
