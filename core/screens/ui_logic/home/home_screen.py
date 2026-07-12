from core.common.ui_bridge import BaseLogicController, create_view_class
from core.common.app_paths import AppPaths
from core.common.error_manager import AppDebugger


class HomeScreen(BaseLogicController):
    def __init__(self, screen_manager):
        # 1. יצירת המחלקה של ה-View (המתכון)
        ViewClass = create_view_class(AppPaths.HOME_SCREEN)
        
        # 2. יצירת המופע (האובייקט הפיזי)
        view_instance = ViewClass()
        
        # 3. אתחול הלוגיקה דרך מחלקת הבסיס
        super().__init__(view_instance)

        self.screen_manager = screen_manager

    def setup_logic(self):
        # שימוש ב-self כי אנחנו יורשים מ-BaseLogicController
        self.safe_connect("btn_go_snippets", "clicked", self._route_to_snippets)
        self.safe_connect("btn_go_ready_code", "clicked", self._route_to_ready_code)

    def load_home_screen(self):
        """טוען ומציג את מסך הבית ומחבר את הנתב המרכזי לכפתורים שלו"""
        AppDebugger.log("מערכת הגשר: טוענת את מסך הבית [home]...")

        # אנחנו רושמים את self.view (המופע שנוצר ב-super().__init__)
        self.screen_manager.register_screen("home", self.view)

        # הצגת האפליקציה
        self.screen_manager.switch_to("home")
        AppDebugger.log("מסך הבית מוכן וממתין למשתמש.\n")

    def _route_to_snippets(self):
        AppDebugger.log("נתב מרכזי: מעביר שליטה ל-SnippetsFlow.")
        self.screen_manager.switch_to("snippets") # Changed to "snippets" as per main.py's registration

    def _route_to_ready_code(self):
        AppDebugger.log("נתב מרכזי: מעביר שליטה ל-ReadyCodeFlow.")
        self.screen_manager.switch_to("ready_code") # Changed to "ready_code" as per main.py's registration