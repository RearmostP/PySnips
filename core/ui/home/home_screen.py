from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QBoxLayout
from core.ui.icons import set_button_icon, NAV_ICON_SIZE


class HomeScreen(QWidget):
    open_snips = Signal()
    open_settings = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        self.cards_layout = self.ui.findChild(QBoxLayout, 'cards_layout')
        set_button_icon(self.ui.findChild(QPushButton, 'open_snips'), 'content/snippet', size=NAV_ICON_SIZE)
        set_button_icon(self.ui.findChild(QPushButton, 'open_settings'), 'navigation/settings', size=NAV_ICON_SIZE)
        self.ui.findChild(QPushButton, 'open_snips').clicked.connect(self.open_snips.emit)
        self.ui.findChild(QPushButton, 'open_settings').clicked.connect(self.open_settings.emit)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Horizontal box layouts mirror automatically with the interface language.
        self.cards_layout.setDirection(
            QBoxLayout.TopToBottom if self.width() < 600 else QBoxLayout.LeftToRight
        )
