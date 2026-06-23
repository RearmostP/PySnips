from core.common.dynamic_ui_loader import create_dynamic_ui_loader
from core.common.app_paths import AppPaths

class HomeScreen(create_dynamic_ui_loader(AppPaths.HOME_SCREEN)):
    def __init__(self, parent=None):
        super().__init__(parent)

