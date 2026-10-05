from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton


class HomeScreen(QWidget):
    open_snips = Signal()
    open_settings = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        self.ui.findChild(QPushButton, 'open_snips').clicked.connect(self.open_snips.emit)
        self.ui.findChild(QPushButton, 'open_settings').clicked.connect(self.open_settings.emit)
