from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QCheckBox, QPushButton
from core.settings.settings import Settings


class GeneralPage(QWidget):
    save_requested = Signal(object)

    def __init__(self, settings, localization, themes, parent=None):
        super().__init__(parent)
        self.localization = localization
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        QVBoxLayout(self).addWidget(self.ui)
        self.language = self.ui.findChild(QComboBox, 'language')
        self.theme = self.ui.findChild(QComboBox, 'theme')
        self.start = self.ui.findChild(QCheckBox, 'start_on_snips')
        for code in localization.available_languages():
            self.language.addItem(localization.language_name(code), code)
        for theme in themes.available_themes():
            self.theme.addItem(localization.text('theme.' + theme) if theme in ('light', 'dark') else theme, theme)
        self.language.setCurrentIndex(max(0, self.language.findData(settings.language)))
        self.theme.setCurrentIndex(max(0, self.theme.findData(settings.theme)))
        self.start.setChecked(settings.start_on_snips)
        self.ui.findChild(QPushButton, 'save').clicked.connect(self.save)

    def save(self):
        self.save_requested.emit(Settings(self.language.currentData(), self.theme.currentData(), self.start.isChecked()))

    def retranslate(self):
        for index in range(self.theme.count()):
            name = self.theme.itemData(index)
            self.theme.setItemText(index, self.localization.text('theme.' + name) if name in ('light', 'dark') else name)
