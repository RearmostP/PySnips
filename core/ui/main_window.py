from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtGui import QIcon
from core.common.paths import ASSETS_DIR
from core.common.user_messages import UserMessageManager
from core.localization.ui_translator import translate_ui
from core.settings.settings import save_settings
from core.snips.models import LibraryError
from core.ui.home.home_screen import HomeScreen
from core.ui.snips.snips_screen import SnipsScreen
from core.ui.settings.settings_screen import SettingsScreen


class MainWindow(QMainWindow):
    def __init__(self, library, settings, localization, themes):
        super().__init__()
        self.library, self.settings, self.localization, self.themes = library, settings, localization, themes
        self.setWindowTitle('PySnips')
        self.setWindowIcon(QIcon(str(ASSETS_DIR / 'icons' / 'pysnips-multisize.ico')))
        self.resize(1024, 768)
        self.messages = UserMessageManager(self, localization)
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)
        self.home = HomeScreen(self)
        self.snips = SnipsScreen(library, localization, self.messages, self)
        self.settings_screen = SettingsScreen(library, settings, localization, themes, self.messages, self)
        for screen in (self.home, self.snips, self.settings_screen):
            self.stack.addWidget(screen)
        self.home.open_snips.connect(self.show_snips)
        self.home.open_settings.connect(self.show_settings)
        self.snips.open_home.connect(self.show_home)
        self.snips.open_settings.connect(self.show_settings)
        self.settings_screen.open_home.connect(self.show_home)
        self.settings_screen.open_snips.connect(self.show_snips)
        self.settings_screen.save_requested.connect(self.apply_settings)
        translate_ui(self, localization)
        self.show_snips() if settings.start_on_snips else self.show_home()

    def show_home(self):
        self.stack.setCurrentWidget(self.home)

    def show_snips(self):
        try:
            self.snips.refresh_categories()
            self.stack.setCurrentWidget(self.snips)
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))

    def show_settings(self):
        self.stack.setCurrentWidget(self.settings_screen)

    def apply_settings(self, settings):
        try:
            save_settings(settings)
            self.themes.apply(settings.theme)
            self.localization.set_language(settings.language)
            self.settings = settings
            translate_ui(self, self.localization)
            self.settings_screen.general.retranslate()
            self.snips.refresh_categories()
        except OSError:
            self.messages.error_key('errors.io')
