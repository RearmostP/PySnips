from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem
from core.localization.ui_translator import translate_ui
from core.snips.models import LibraryError


class DeletedSnippets(QDialog):
    def __init__(self, library, localization, messages, parent=None):
        super().__init__(parent)
        self.library, self.localization, self.messages = library, localization, messages
        self.setWindowTitle(localization.text('settings.deleted'))
        self.resize(650, 450)
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        QVBoxLayout(self).addWidget(self.ui)
        self.items = self.ui.findChild(QListWidget, 'snippets')
        self.ui.findChild(QPushButton, 'restore').clicked.connect(self.restore)
        self.ui.findChild(QPushButton, 'permanent').clicked.connect(self.permanent)
        self.ui.findChild(QPushButton, 'close').clicked.connect(self.accept)
        self.items.currentRowChanged.connect(self.selection_changed)
        translate_ui(self, localization)
        self.refresh()

    def refresh(self):
        try:
            self.items.clear()
            for snippet in self.library.deleted():
                item = QListWidgetItem(snippet.title + ' · ' + snippet.category, self.items)
                item.setData(Qt.ItemDataRole.UserRole, snippet.id)
            self.selection_changed()
        except (LibraryError, OSError) as error:
            self.messages.data_error(error)

    def selection_changed(self):
        for name in ('restore', 'permanent'):
            self.ui.findChild(QPushButton, name).setEnabled(self.items.currentItem() is not None)

    def restore(self):
        item = self.items.currentItem()
        if item:
            try:
                self.library.restore(item.data(Qt.ItemDataRole.UserRole))
                self.refresh()
            except (LibraryError, OSError) as error:
                self.messages.data_error(error)

    def permanent(self):
        item = self.items.currentItem()
        if item and self.messages.confirm(self.localization.text('trash.confirm_permanent')):
            try:
                self.library.permanently_delete(item.data(Qt.ItemDataRole.UserRole))
                self.refresh()
            except (LibraryError, OSError) as error:
                self.messages.data_error(error)
