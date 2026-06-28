from PySide6.QtWidgets import QMenu

from core.common.app_paths import AppPaths
from core.common.dynamic_ui_loader import create_dynamic_ui_loader
from core.common.error_manager import AppDebugger, AppErrorHandler






class SnippetsScreen(create_dynamic_ui_loader(AppPaths.SNIPPETS_SCREEN)):
    def __init__(self, parent=None):
        super().__init__(parent)


    def setup_events(self):
        """
        פונקציה שמחברת את האירועים והכפתורים.
        נקראת רק לאחר שקובץ ה-UI נטען במלואו לזיכרון על ידי SnippetsFlow שב app_coordinator.py.
        """
        AppDebugger.log(" SnippetsScreen: מחבר אירועים ורכיבי ממשק...")

        # בניית תפריט ההמבורגר (☰)
        self.setup_hamburger_menu()

    def setup_hamburger_menu(self):
        """מגדיר ומצמיד תפריט קופץ עבור כפתור ה-3 פסים"""
        self.hamburger_menu = QMenu(self)

        action_home = self.hamburger_menu.addAction("🏠 בית")
        action_settings = self.hamburger_menu.addAction("⚙️ הגדרות")
        action_about = self.hamburger_menu.addAction("ℹ️ אודות")

        action_home.triggered.connect(self.go_back_home)
        action_settings.triggered.connect(self.open_settings)
        action_about.triggered.connect(self.show_about)

        self.btn_menu.setMenu(self.hamburger_menu)


# ----------------------------------------------------------------
    def go_back_home(self):
        """חזרה למסך הבית באמצעות מנהל המסכים"""
        if hasattr(self, 'manager') and self.manager:
            AppDebugger.log("🏠 SnippetsScreen: חוזר למסך הבית...")
            self.manager.switch_to("home")

    def open_settings(self):
        """פתיחת חלון הגדרות"""
        AppDebugger.log("⚙️ SnippetsScreen: פתיחת הגדרות...")

    def show_about(self):
        """הצגת מידע אודות היישום"""
        AppDebugger.log("ℹ️ SnippetsScreen: הצגת מידע אודות...")
#---------------------------------------------------------------------



