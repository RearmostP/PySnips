from core.common.app_paths import AppPaths
from core.common.dynamic_ui_loader import create_dynamic_ui_loader


class CreateSnipDialog(create_dynamic_ui_loader(AppPaths.CREATE_SNIPS_DIALOG)):
    def __init__(self, parent=None):
        super().__init__(parent)
