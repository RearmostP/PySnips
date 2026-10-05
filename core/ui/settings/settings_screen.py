from pathlib import Path
from PySide6.QtCore import Signal, QSignalBlocker, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QComboBox, QCheckBox, QLabel
from core.localization.ui_translator import translate_ui
from core.settings.settings import Settings
from core.ui.snips.dialogs.deleted_snippets import DeletedSnippets
from core.ui.dialogs.about_dialog import AboutDialog
from core.snips.models import LibraryError


class SettingsScreen(QWidget):
    back_requested = Signal()
    save_requested = Signal(object)

    def __init__(self, library, settings, localization, themes, messages, parent=None):
        super().__init__(parent)
        self.library, self.localization, self.messages = library, localization, messages
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        self.language = self.ui.findChild(QComboBox, 'language')
        self.theme = self.ui.findChild(QComboBox, 'theme')
        self.start = self.ui.findChild(QCheckBox, 'start_on_snips')
        for code in localization.available_languages():
            self.language.addItem(localization.language_name(code), code)
        for name in themes.available_themes():
            self.theme.addItem(name, name)
        self.retranslate(settings)
        self.language.currentIndexChanged.connect(self.save)
        self.theme.currentIndexChanged.connect(self.save)
        self.start.toggled.connect(self.save)
        self.ui.findChild(QPushButton, 'deleted').clicked.connect(self.show_deleted)
        self.ui.findChild(QPushButton, 'rebuild').clicked.connect(self.rebuild)
        self.ui.findChild(QPushButton, 'about').clicked.connect(lambda: AboutDialog(localization, self).exec())
        self.ui.findChild(QPushButton, 'back').clicked.connect(self.back_requested.emit)

    def save(self):
        self.save_requested.emit(Settings(self.language.currentData(), self.theme.currentData(), self.start.isChecked()))

    def retranslate(self, settings=None):
        with QSignalBlocker(self.language), QSignalBlocker(self.theme), QSignalBlocker(self.start):
            translate_ui(self, self.localization)
            alignment = Qt.AlignRight if self.localization.rtl else Qt.AlignLeft
            self.ui.findChild(QLabel, 'about_title').setAlignment(alignment | Qt.AlignAbsolute | Qt.AlignVCenter)
            for index in range(self.theme.count()):
                name = self.theme.itemData(index)
                self.theme.setItemText(index, self.localization.text('theme.' + name) if name in ('light', 'dark') else name)
            if settings is not None:
                self.language.setCurrentIndex(max(0, self.language.findData(settings.language)))
                self.theme.setCurrentIndex(max(0, self.theme.findData(settings.theme)))
                self.start.setChecked(settings.start_on_snips)

    def show_deleted(self):
        DeletedSnippets(self.library, self.localization, self.messages, self).exec()

    def rebuild(self):
        try:
            self.library.rebuild_search()
            self.messages.info(self.localization.text('settings.rebuilt'))
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))
