from pathlib import Path
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QPushButton,
                               QLabel, QInputDialog, QMenu)
from core.snips.models import LibraryError
from core.common.paths import ASSETS_DIR
from core.localization.ui_translator import translate_ui
from core.ui.snips.widgets.snippet_search import SnippetSearch
from core.ui.snips.widgets.snippet_card import SnippetCard
from core.ui.snips.dialogs.create_snippet import CreateSnippet
from core.ui.snips.dialogs.snippet_details import SnippetDetails
from core.ui.dialogs.about_dialog import AboutDialog


class SnipsScreen(QWidget):
    open_home = Signal()
    open_settings = Signal()

    def __init__(self, library, localization, messages, parent=None):
        super().__init__(parent)
        self.library, self.localization, self.messages = library, localization, messages
        self.current_category = None
        self.category_buttons = []
        self.cards = []
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        self.category_layout = self.ui.findChild(QVBoxLayout, 'categories_dynamic_layout')
        self.card_layout = self.ui.findChild(QGridLayout, 'grid_snippets_layout')
        self.category_title = self.ui.findChild(QLabel, 'category_title')
        # Dynamic category headings are translated explicitly from semantic keys.
        self.category_title.setProperty('i18nKey', None)
        self.search = SnippetSearch(self)
        search_layout = QVBoxLayout(self.ui.findChild(QWidget, 'search_holder'))
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.addWidget(self.search)
        self.menu = QMenu(self)
        menu_button = self.ui.findChild(QPushButton, 'menu')
        menu_button.setText('')
        menu_button.setIcon(QIcon(str(ASSETS_DIR / 'icons' / 'hamburger.svg')))
        menu_button.setIconSize(QSize(20, 20))
        menu_button.setMenu(self.menu)
        self.ui.findChild(QPushButton, 'create').clicked.connect(self.create)
        self.ui.findChild(QPushButton, 'add_category').clicked.connect(self.add_category)
        self.search.changed.connect(self.refresh)

    @staticmethod
    def clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()

    def refresh_categories(self):
        try:
            categories = self.library.categories()
            if self.current_category not in categories:
                self.current_category = None
            self.clear_layout(self.category_layout)
            self.category_buttons = []
            for category in [None, *categories]:
                title = (self.localization.text('snips.folder', category=category)
                         if category else self.localization.text('snips.recent'))
                button = QPushButton(title, self.ui)
                button.setProperty('categoryNav', True)
                button.setMinimumHeight(35)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.clicked.connect(lambda checked=False, value=category: self.select_category(value))
                self.category_layout.addWidget(button)
                self.category_buttons.append((category, button))
            self.category_layout.addStretch()
            self.menu.clear()
            self.menu.addAction(self.localization.text('nav.home'), self.open_home.emit)
            self.menu.addAction(self.localization.text('nav.settings'), self.open_settings.emit)
            self.menu.addAction(self.localization.text('settings.about'),
                                lambda: AboutDialog(self.localization, self).exec())
            self.refresh()
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))

    def select_category(self, category):
        self.current_category = category
        self.search.query.clear()
        self.search.timer.stop()
        self.refresh()

    def refresh(self):
        try:
            query = self.search.query.text().strip()
            snippets = self.library.search(query, None if query else self.current_category)
            if not query and self.current_category is None:
                snippets = sorted(snippets, key=lambda s: s.created_at, reverse=True)
            self.clear_layout(self.card_layout)
            for row in range(self.card_layout.rowCount()):
                self.card_layout.setRowStretch(row, 0)
            self.cards = []
            for row, snippet in enumerate(snippets):
                card = SnippetCard(snippet, self.library.media_base(snippet.id), self.localization, self.ui)
                card.details_requested.connect(self.open_snippet)
                card.edit_requested.connect(self.edit_snippet)
                card.delete_requested.connect(self.delete_snippet)
                self.card_layout.addWidget(card, row, 0)
                self.cards.append(card)
            if not snippets:
                empty = QLabel(self.localization.text('snips.no_results'), self.ui)
                empty.setObjectName('snippets_empty')
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.card_layout.addWidget(empty, 0, 0)
            self.card_layout.setRowStretch(len(snippets) + 1, 1)
            for button in [self.ui.findChild(QPushButton, 'menu'),
                           self.ui.findChild(QPushButton, 'add_category'),
                           *(button for _, button in self.category_buttons)]:
                if button.property('navRtl') != self.localization.rtl:
                    button.setProperty('navRtl', self.localization.rtl)
                    button.style().unpolish(button)
                    button.style().polish(button)
            translate_ui(self, self.localization)
            title = (self.localization.text('snips.search_title') if query else
                     self.localization.text('snips.folder', category=self.current_category)
                     if self.current_category else self.localization.text('snips.recent'))
            self.category_title.setText(title)
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))

    def create(self):
        try:
            dialog = CreateSnippet(self.library, self.localization, self.messages, parent=self)
            if self.current_category is not None:
                dialog.category.setCurrentText(self.current_category)
            if dialog.exec():
                self.refresh()
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))

    def open_snippet(self, snippet_id):
        try:
            snippet = self.library.load(snippet_id)
            SnippetDetails(self.library, self.localization, self.messages, snippet, self).exec()
            self.refresh()
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))

    def edit_snippet(self, snippet_id):
        try:
            snippet = self.library.load(snippet_id)
            if CreateSnippet(self.library, self.localization, self.messages, snippet, self).exec():
                self.refresh()
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))

    def delete_snippet(self, snippet_id):
        if self.messages.confirm(self.localization.text('snips.confirm_delete')):
            try:
                self.library.delete(snippet_id)
                self.refresh()
            except (LibraryError, OSError) as error:
                self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))

    def add_category(self):
        name, accepted = QInputDialog.getText(self, self.localization.text('snips.add_category'),
                                             self.localization.text('snips.category'))
        if accepted:
            try:
                self.library.add_category(name)
                self.refresh_categories()
            except (LibraryError, OSError) as error:
                self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))
