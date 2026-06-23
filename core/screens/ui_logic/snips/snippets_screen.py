import os
from PySide6.QtWidgets import QMenu

from core.common.app_paths import AppPaths
from core.common.dynamic_ui_loader import create_dynamic_ui_loader
from core.common.error_manager import AppDebugger, AppErrorHandler


class SnippetsScreen(create_dynamic_ui_loader(AppPaths.SNIPPETS_SCREEN)):
    def __init__(self, parent=None):
        super().__init__(parent)

        # מצב התחלתי של הסרגל
        self.sidebar_expanded = True

    def setup_events(self):
        """
        פונקציה שמחברת את האירועים והכפתורים.
        נקראת רק לאחר שקובץ ה-UI נטען במלואו לזיכרון.
        """
        AppDebugger.log(" SnippetsScreen: מחבר אירועים ורכיבי ממשק...")

        # תיקון: גישה ישירה ל-self ללא .ui
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)

        # בניית תפריט ההמבורגר (☰)
        self.setup_hamburger_menu()

    def setup_hamburger_menu(self):
        """מגדיר ומצמיד תפריט קופץ עבור כפתור ה-3 פסים"""
        self.hamburger_menu = QMenu(self)

        action_home = self.hamburger_menu.addAction("🏠 בית")
        action_settings = self.hamburger_menu.addAction("⚙️ הגדרות")

        action_home.triggered.connect(self.go_back_home)

        # תיקון: גישה ישירה ל-self ללא .ui
        self.btn_menu.setMenu(self.hamburger_menu)

    def toggle_sidebar(self):
        """מצמצם או מרחיב את הסרגל הימני בלחיצת כפתור"""
        if self.sidebar_expanded:
            # תיקון: גישה ישירה ל-self ללא .ui
            self.wdg_sidebar.setFixedWidth(50)
            self.btn_toggle_sidebar.setText("◀")
            self.sidebar_expanded = False
        else:
            # תיקון: גישה ישירה ל-self ללא .ui
            self.wdg_sidebar.setFixedWidth(200)
            self.btn_toggle_sidebar.setText("▶")
            self.sidebar_expanded = True

    def go_back_home(self):
        """חזרה למסך הבית באמצעות מנהל המסכים"""
        if hasattr(self, 'manager') and self.manager:
            AppDebugger.log("🏠 SnippetsScreen: חוזר למסך הבית...")
            self.manager.switch_to("home")