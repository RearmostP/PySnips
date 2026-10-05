from pathlib import Path
from PySide6.QtCore import Signal, QSize
from PySide6.QtGui import QIcon
from core.common.paths import ASSETS_DIR
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QStackedWidget
from core.ui.settings.pages.general import GeneralPage
from core.ui.settings.pages.snips import SnipsPage
from core.ui.snips.dialogs.deleted_snippets import DeletedSnippets
from core.snips.models import LibraryError


class SettingsScreen(QWidget):
    open_home = Signal()
    open_snips = Signal()
    save_requested = Signal(object)

    def __init__(self, library, settings, localization, themes, messages, parent=None):
        super().__init__(parent)
        self.library, self.localization, self.messages = library, localization, messages
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        self.general = GeneralPage(settings, localization, themes, self)
        self.snips = SnipsPage(self)
        self.pages = self.ui.findChild(QStackedWidget, 'wdg_settings_pages')
        self.pages.addWidget(self.general)
        self.pages.addWidget(self.snips)
        self.general.save_requested.connect(self.save_requested.emit)
        self.snips.deleted_requested.connect(self.show_deleted)
        self.snips.rebuild_requested.connect(self.rebuild)
        self.ui.findChild(QPushButton, 'general_button').clicked.connect(lambda: self.show_page(self.general))
        self.ui.findChild(QPushButton, 'snips_button').clicked.connect(lambda: self.show_page(self.snips))
        self.ui.findChild(QPushButton, 'deleted').clicked.connect(self.show_deleted)
        self.ui.findChild(QPushButton, 'home').clicked.connect(self.open_home.emit)
        self.ui.findChild(QPushButton, 'snips').clicked.connect(self.open_snips.emit)
        self.ui.findChild(QPushButton, 'about').clicked.connect(lambda: messages.info(localization.text('settings.about_text')))
        self.show_page(self.general)

    def show_page(self, page):
        self.pages.setCurrentWidget(page)
        for name, target in [('general_button', self.general), ('snips_button', self.snips)]:
            button = self.ui.findChild(QPushButton, name)
            button.setProperty('active', page is target)
            button.style().unpolish(button)
            button.style().polish(button)
        self.ui.findChild(QWidget, 'wdg_snips_submenu').setVisible(page is self.snips)
        button = self.ui.findChild(QPushButton, 'snips_button')
        icon = 'chevron-down.svg' if page is self.snips else 'chevron-right.svg'
        button.setIcon(QIcon(str(ASSETS_DIR / 'icons' / icon)))
        button.setIconSize(QSize(14, 14))

    def show_deleted(self):
        DeletedSnippets(self.library, self.localization, self.messages, self).exec()

    def rebuild(self):
        try:
            self.library.rebuild_search()
            self.messages.info(self.localization.text('settings.rebuilt'))
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))
