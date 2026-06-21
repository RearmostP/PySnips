from core.common.dynamic_ui_loader import DynamicUiLoader

class HomeScreen(DynamicUiLoader):
    def __init__(self, parent=None):
        super().__init__("fine_name.ui", parent)

