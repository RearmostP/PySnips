# core/app_paths.py
#
from pathlib import Path

class AppPaths:
    # מאתרים את תיקיית השורש של הפרויקט באופן דינמי
    PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
    CORE_DIR = PROJECT_DIR / "core"
    COMMON_DIR = str(CORE_DIR / "common")
    UI_DIR = PROJECT_DIR / "core" / "ui"
    LOGS_DIR = PROJECT_DIR / "logs"

    # נתיבים מוחלטים לכל קובצי ה-UI
    HOME_SCREEN = UI_DIR / "home_screen.ui"
    SNIPPETS_SCREEN = UI_DIR / "snippets_screen.ui"
    READY_CODE_SCREEN = UI_DIR / "ready_code_screen.ui"