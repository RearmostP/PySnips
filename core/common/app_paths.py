# core/app_paths.py
#
from pathlib import Path

class AppPaths:
    # מאתרים את תיקיית השורש של הפרויקט באופן דינמי
    PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

    ASSETS_DIR = PROJECT_DIR / "assets"

    ICONS_DIR = ASSETS_DIR / "icons"

    APP_ICON = str(ICONS_DIR / "PySnips.ico")

    CORE_DIR = PROJECT_DIR / "core"

    COMMON_DIR = CORE_DIR / "common"


    UI_DIR = PROJECT_DIR / "core" / "screens" / "ui"

    UI_LOGIC_DIR =CORE_DIR / "screens" / "ui_logic"

    LOGS_DIR = PROJECT_DIR / "logs"

    # נתיבים מוחלטים לכל קובצי ה-UI
    HOME_SCREEN = str(UI_DIR / "home_screen.ui")
    SNIPPETS_SCREEN = UI_DIR / "snippets_screen.ui"
    READY_CODE_SCREEN = UI_DIR / "ready_code_screen.ui"