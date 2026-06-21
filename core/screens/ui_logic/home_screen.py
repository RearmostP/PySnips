import core.common.app_paths
from core.common.dynamic_ui_loader import DynamicUiLoader
from core.common.app_paths import AppPaths

class HomeScreen(DynamicUiLoader):
    def __init__(self, parent=None):
        super().__init__(AppPaths.HOME_SCREEN, parent)

    # def go_to_snippets(self):
    #     # אנחנו פונים לאבא שלנו (ה-ScreenManager) ומבקשים לעבור מסך
    #     if self.parent():
    #         self.parent().switch_to("snippets")