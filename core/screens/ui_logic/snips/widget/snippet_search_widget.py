from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QSizePolicy, QSpacerItem, QWidget

from core.screens.ui_logic.snips.widget.snippet_card import SnippetCard
from core.tools.common.app_paths import AppPaths
from core.tools.common.dynamic_ui_loader import create_dynamic_ui_loader
from core.tools.common.error_manager import AppDebugger, AppErrorHandler
from core.tools.search.snippet_search_engine import SnippetSearchEngine


class SnippetSearchWidget(create_dynamic_ui_loader(AppPaths.SNIPPET_SEARCH_WIDGET)):
    edit_requested = Signal(dict)
    details_requested = Signal(dict)

    PAGE_SIZE = 8
    MIN_QUERY_LENGTH = 1

    def __init__(self, parent: QWidget | None = None, search_engine: SnippetSearchEngine | None = None):
        super().__init__(parent)
        self.search_engine = search_engine or SnippetSearchEngine()
        self._query = ""
        self._results: list[dict] = []
        self._visible_count = 0
        self._bottom_spacer: QSpacerItem | None = None

        self.setup_logic()
        self._setup_styles()
        self.clear()

    def setup_logic(self):
        self.btn_load_more.clicked.connect(self.load_next_page)

    def set_query(self, query: str):
        query = (query or "").strip()
        if query == self._query:
            return

        self._query = query
        self._clear_cards()

        if len(query) < self.MIN_QUERY_LENGTH:
            self._results = []
            self._visible_count = 0
            self._set_status("הקלד לפחות 1 תווים כדי לחפש")
            self.btn_load_more.hide()
            return

        try:
            AppDebugger.log(f"SnippetSearchWidget: searching snippets for query: {query}")
            self._results = self.search_engine.search(query)
            self._visible_count = 0
            if not self._results:
                self._set_status("לא נמצאו תוצאות")
                self.btn_load_more.hide()
                return

            self._set_status("")
            self.load_next_page()
        except Exception as e:
            self._results = []
            self._visible_count = 0
            self.btn_load_more.hide()
            self._set_status("שגיאה בחיפוש")
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="שגיאה בחיפוש snippets",
                dev_message=f"SnippetSearchWidget: search failed: {str(e)}",
                severity="ERROR",
            )

    def clear(self):
        self._query = ""
        self._results = []
        self._visible_count = 0
        self._clear_cards()
        self._set_status("")
        self.btn_load_more.hide()

    def load_next_page(self):
        if self._visible_count >= len(self._results):
            self.btn_load_more.hide()
            return

        self._remove_bottom_spacer()
        next_visible_count = min(self._visible_count + self.PAGE_SIZE, len(self._results))

        for snippet_meta in self._results[self._visible_count:next_visible_count]:
            snippet_card = self._create_snippet_card(snippet_meta)
            self.results_layout.addWidget(snippet_card.get_view())

        self._visible_count = next_visible_count
        self.btn_load_more.setVisible(self._visible_count < len(self._results))
        self._add_bottom_spacer()

    def _create_snippet_card(self, snippet_meta: dict) -> SnippetCard:
        snippet_card = SnippetCard(snippet_meta=snippet_meta)
        snippet_card.edit_requested.connect(self.edit_requested.emit)
        snippet_card.details_requested.connect(self.details_requested.emit)
        return snippet_card

    def _clear_cards(self):
        self._bottom_spacer = None
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.spacerItem():
                del item

    def _set_status(self, text: str):
        self.lbl_status.setText(text)
        self.lbl_status.setVisible(bool(text))

    def _add_bottom_spacer(self):
        self._bottom_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.results_layout.addItem(self._bottom_spacer)

    def _remove_bottom_spacer(self):
        if self._bottom_spacer is None:
            return

        for index in range(self.results_layout.count()):
            item = self.results_layout.itemAt(index)
            if item and item.spacerItem() is self._bottom_spacer:
                self.results_layout.takeAt(index)
                break
        self._bottom_spacer = None

    def _setup_styles(self):
        self.setStyleSheet("""
            QLabel#lbl_status {
                color: #a8a8a8;
                font-size: 14px;
                padding: 16px;
            }
            QPushButton#btn_load_more {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#btn_load_more:hover {
                background-color: #333333;
            }
            QPushButton#btn_load_more:pressed {
                background-color: #242424;
            }
        """)

    def get_view(self) -> QWidget:
        return self
