from pathlib import Path
from PySide6.QtCore import Signal, QTimer
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit


class SnippetSearch(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        self.query = self.ui.findChild(QLineEdit, 'query')
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.changed.emit)
        self.query.textChanged.connect(lambda: self.timer.start())
