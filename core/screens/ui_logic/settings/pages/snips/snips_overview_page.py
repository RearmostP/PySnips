# תפקיד הקובץ:
# עמוד הכניסה להגדרות השליפים.
# מציג קישורים פנימיים לפעולות משנה כמו שחזור שליפים וניהול קטגוריות,
# ומשדר signals לחלון ההגדרות כדי לעבור לעמוד המתאים.

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from core.tools.common.app_paths import AppPaths
from core.tools.common.dynamic_ui_loader import create_dynamic_ui_loader


class SnipsOverviewPage(create_dynamic_ui_loader(AppPaths.SNIPS_OVERVIEW_PAGE)):
    restore_requested = Signal()
    categories_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.btn_restore_link.clicked.connect(self.restore_requested.emit)
        self.btn_categories_link.clicked.connect(self.categories_requested.emit)

    def get_view(self) -> QWidget:
        return self
