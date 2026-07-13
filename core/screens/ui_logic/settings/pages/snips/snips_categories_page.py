# תפקיד הקובץ:
# לוגיקת עמוד ניהול קטגוריות השליפים.
# כרגע העמוד משמש כשלד לפיתוח עתידי של פעולות כמו מחיקה, עריכה,
# ושינוי קטגוריות.

from PySide6.QtWidgets import QWidget

from core.tools.common.app_paths import AppPaths
from core.tools.common.dynamic_ui_loader import create_dynamic_ui_loader


class SnipsCategoriesPage(create_dynamic_ui_loader(AppPaths.SNIPS_CATEGORIES_PAGE)):
    def get_view(self) -> QWidget:
        return self
