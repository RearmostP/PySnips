from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton


class SnipsPage(QWidget):
    deleted_requested = Signal()
    rebuild_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        QVBoxLayout(self).addWidget(self.ui)
        self.ui.findChild(QPushButton, 'deleted').clicked.connect(self.deleted_requested.emit)
        self.ui.findChild(QPushButton, 'rebuild').clicked.connect(self.rebuild_requested.emit)
