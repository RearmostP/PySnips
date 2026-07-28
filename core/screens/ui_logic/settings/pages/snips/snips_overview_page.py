# תפקיד הקובץ:
# עמוד הכניסה להגדרות השליפים.
# מציג קישורים פנימיים לפעולות משנה כמו שחזור שליפים וניהול קטגוריות,
# ומשדר signals לחלון ההגדרות כדי לעבור לעמוד המתאים.

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QWidget

from core.tools.common.app_paths import AppPaths
from core.tools.common.dynamic_ui_loader import create_dynamic_ui_loader
from core.tools.settings.snips_settings import load_snips_settings, save_snips_settings


class SnipsOverviewPage(create_dynamic_ui_loader(AppPaths.SNIPS_OVERVIEW_PAGE)):
    restore_requested = Signal()
    categories_requested = Signal()
    display_settings_changed = Signal()

    SNIPPET_CARD_HEIGHTS = range(300, 901, 50)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._load_snippet_card_height_options()
        self.btn_restore_link.clicked.connect(self.restore_requested.emit)
        self.btn_categories_link.clicked.connect(self.categories_requested.emit)
        self.cmb_snippet_card_height.currentTextChanged.connect(
            self._save_snippet_card_height
        )

    def _load_snippet_card_height_options(self) -> None:
        blocker = QSignalBlocker(self.cmb_snippet_card_height)
        self.cmb_snippet_card_height.clear()
        self.cmb_snippet_card_height.addItems(
            [str(height) for height in self.SNIPPET_CARD_HEIGHTS]
        )
        settings = load_snips_settings()
        self.cmb_snippet_card_height.setCurrentText(
            str(settings.display.snippet_card_height)
        )
        del blocker

    def _save_snippet_card_height(self, value: str) -> None:
        try:
            snippet_card_height = int(value)
        except ValueError:
            return

        settings = load_snips_settings()
        if settings.display.snippet_card_height == snippet_card_height:
            return

        settings.display.snippet_card_height = snippet_card_height
        if save_snips_settings(settings):
            self.display_settings_changed.emit()

    def get_view(self) -> QWidget:
        return self
