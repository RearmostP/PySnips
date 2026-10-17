from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem
from core.localization.ui_translator import translate_ui
from core.snips.models import LibraryError
from core.ui.icons import set_button_icon


class DeletedSnippets(QDialog):
    def __init__(self, library, localization, messages, parent=None):
        super().__init__(parent)
        self.library, self.localization, self.messages = library, localization, messages
        self.setWindowTitle(localization.text('trash.title'))
        self.resize(650, 560)
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        QVBoxLayout(self).addWidget(self.ui)
        self.items = self.ui.findChild(QListWidget, 'snippets')
        self.category_items = self.ui.findChild(QListWidget, 'categories')
        for name, glyph in (('restore', 'actions/restore'), ('restore_category', 'actions/restore'),
                            ('permanent', 'actions/delete'), ('permanent_category', 'actions/delete'),
                            ('close', 'actions/close')):
            set_button_icon(self.ui.findChild(QPushButton, name), glyph)
        self.ui.findChild(QPushButton, 'restore_category').clicked.connect(self.restore_category)
        self.ui.findChild(QPushButton, 'permanent_category').clicked.connect(self.permanent_category)
        self.ui.findChild(QPushButton, 'restore').clicked.connect(self.restore)
        self.ui.findChild(QPushButton, 'permanent').clicked.connect(self.permanent)
        self.ui.findChild(QPushButton, 'close').clicked.connect(self.accept)
        self.items.currentRowChanged.connect(self.selection_changed)
        self.category_items.currentRowChanged.connect(self.selection_changed)
        translate_ui(self, localization)
        self.refresh()

    def refresh(self):
        try:
            self.items.clear()
            self.category_items.clear()
            self.category_items.addItems(self.library.deleted_categories())
            for snippet in self.library.deleted():
                item = QListWidgetItem(snippet.title + ' · ' + snippet.category, self.items)
                item.setData(Qt.ItemDataRole.UserRole, snippet.id)
            self.selection_changed()
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))

    def selection_changed(self):
        for name in ('restore', 'permanent'):
            self.ui.findChild(QPushButton, name).setEnabled(self.items.currentItem() is not None)
        for name in ('restore_category', 'permanent_category'):
            self.ui.findChild(QPushButton, name).setEnabled(self.category_items.currentItem() is not None)

    def restore_category(self):
        self._category_action(False)

    def permanent_category(self):
        self._category_action(True)

    def _category_action(self, permanent):
        item = self.category_items.currentItem()
        if item is None:
            return
        name = item.text()
        if permanent and not self.messages.confirm(
                self.localization.text('category.confirm_permanent', category=name)):
            return
        try:
            if permanent:
                self.library.permanently_delete_category(name)
            else:
                self.library.restore_category(name)
            self.refresh()
            self.messages.info(self.localization.text(
                'category.removed' if permanent else 'category.restored', category=name))
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))

    def restore(self):
        item = self.items.currentItem()
        if item:
            try:
                self.library.restore(item.data(Qt.ItemDataRole.UserRole))
                self.refresh()
            except (LibraryError, OSError) as error:
                self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))

    def permanent(self):
        item = self.items.currentItem()
        if item and self.messages.confirm(self.localization.text('trash.confirm_permanent')):
            try:
                self.library.permanently_delete(item.data(Qt.ItemDataRole.UserRole))
                self.refresh()
            except (LibraryError, OSError) as error:
                self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))
