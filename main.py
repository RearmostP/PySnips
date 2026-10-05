"""Explicit startup. No boot framework or developer diagnostics in runtime."""
import sys
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication
from core.common.paths import ASSETS_DIR
from core.common.user_messages import UserMessageManager
from core.localization.localization import Localization
from core.settings.settings import Settings, load_settings
from core.snips.library import SnippetLibrary
from core.snips.models import LibraryError
from core.theme.theme_manager import ThemeManager
from core.ui.main_window import MainWindow


def load_fonts():
    for path in (ASSETS_DIR / 'fonts').glob('*'):
        if path.suffix.lower() in ('.ttf', '.otf'):
            QFontDatabase.addApplicationFont(str(path))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('PySnips')
    app.setWindowIcon(QIcon(str(ASSETS_DIR / 'icons' / 'pysnips-multisize.ico')))
    load_fonts()
    localization = Localization()
    messages = UserMessageManager(None, localization)
    try:
        settings = load_settings()
    except (OSError, ValueError):
        messages.warning(localization.text('errors.settings'))
        settings = Settings()
    localization.set_language(settings.language)
    themes = ThemeManager(app)
    themes.apply(settings.theme)
    try:
        library = SnippetLibrary()
    except (LibraryError, OSError) as error:
        messages.data_error(error)
        return 1
    window = MainWindow(library, settings, localization, themes)
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
