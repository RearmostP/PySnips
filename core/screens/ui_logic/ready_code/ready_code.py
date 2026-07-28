from PySide6.QtWidgets import QWidget

from core.tools.common.app_paths import AppPaths
from core.tools.common.dynamic_ui_loader import create_dynamic_ui_loader
from core.tools.common.error_manager import AppDebugger


class ReadyCodeScreen(create_dynamic_ui_loader(AppPaths.READY_CODE_SCREEN)):
    """מסך הקוד המוכן הבסיסי, כולל ניווט תקין חזרה למסך הבית."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.btn_back_home.clicked.connect(self.go_back_home)

    def go_back_home(self):
        if hasattr(self, "manager") and self.manager:
            self.manager.switch_to("home")

class ReadyCodeFlow:
    """מחלקה עצמאית שמנהלת את סדר הפעולות והלוגיקה של מסך קוד מוכן"""

    def __init__(self, screen_manager):
        self.screen_manager = screen_manager

    def start(self):
        AppDebugger.log("ReadyCodeFlow: מתחיל סדר פעולות עבור מסך קוד מוכן...")
        # כאן תבוא הלוגיקה הבאה של מסך הקוד המוכן כשתבנה אותו
        self.screen_manager.switch_to("ready_code")
