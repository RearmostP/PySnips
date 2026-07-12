from core.common.dynamic_ui_loader import create_dynamic_ui_loader
from core.common.error_manager import AppDebugger
from core.common.app_paths import AppPaths
from PySide6.QtWidgets import QWidget # For type hinting


class HomeScreen(create_dynamic_ui_loader(AppPaths.HOME_SCREEN)): # Inherit directly
    def __init__(self, screen_manager: QWidget | None = None): # Parent is now screen_manager
        super().__init__(screen_manager) # Pass screen_manager as parent
        self.screen_manager = screen_manager
        
        # Initialize logic
        self.setup_logic()

    def setup_logic(self):
        # Direct connection to UI elements
        self.btn_go_snippets.clicked.connect(self._route_to_snippets)
        self.btn_go_ready_code.clicked.connect(self._route_to_ready_code)

    def load_home_screen(self):
        """טוען ומציג את מסך הבית ומחבר את הנתב המרכזי לכפתורים שלו"""
        AppDebugger.log("מערכת הגשר: טוענת את מסך הבית [home]...")

        # אנחנו רושמים את self (המופע שנוצר ב-super().__init__)
        self.screen_manager.register_screen("home", self) # Register self as the screen

        # הצגת האפליקציה
        self.screen_manager.switch_to("home")
        AppDebugger.log("מסך הבית מוכן וממתין למשתמש.\n")

    def _route_to_snippets(self):
        AppDebugger.log("נתב מרכזי: מעביר שליטה ל-SnippetsFlow.")
        self.screen_manager.switch_to("snippets")

    def _route_to_ready_code(self):
        AppDebugger.log("נתב מרכזי: מעביר שליטה ל-ReadyCodeFlow.")
        self.screen_manager.switch_to("ready_code")