# תפקיד הקובץ:
# אתחול קבצי ההגדרות בזמן עליית האפליקציה.
# אם חסר קובץ הגדרות תחת data/system_data/settings, הקובץ יוצר אותו עם
# ערכי ברירת מחדל בלי לדרוס קבצים קיימים של המשתמש.

from core.tools.common.app_paths import AppPaths
from core.tools.common.error_manager import AppDebugger, AppErrorHandler
from core.tools.settings.settings_store import save_json_settings
from core.tools.settings.snips_settings import DEFAULT_SNIPS_SETTINGS, load_snips_settings, save_snips_settings


DEFAULT_GENERAL_SETTINGS = {}
DEFAULT_READY_CODE_SETTINGS = {}


def ensure_settings_files_exist() -> bool:
    """יוצר קבצי הגדרות חסרים עם ערכי ברירת מחדל."""
    try:
        AppPaths.SETTINGS_DATA_DIR.mkdir(parents=True, exist_ok=True)

        _ensure_general_settings_file()
        _ensure_snips_settings_file()
        _ensure_ready_code_settings_file()

        AppDebugger.log("אתחול הגדרות: קבצי ההגדרות מוכנים.")
        return True
    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאה באתחול קבצי ההגדרות",
            dev_message=f"אתחול הגדרות: בדיקת או יצירת קבצי ההגדרות נכשלה: {str(e)}",
            severity="ERROR",
            show_gui=False,
        )
        return False


def _ensure_general_settings_file() -> None:
    if AppPaths.GENERAL_SETTINGS_JSON.exists():
        return
    save_json_settings(AppPaths.GENERAL_SETTINGS_JSON, DEFAULT_GENERAL_SETTINGS)


def _ensure_snips_settings_file() -> None:
    if AppPaths.SNIPS_SETTINGS_JSON.exists():
        return

    settings = load_snips_settings()
    if not save_snips_settings(settings):
        save_json_settings(AppPaths.SNIPS_SETTINGS_JSON, DEFAULT_SNIPS_SETTINGS)


def _ensure_ready_code_settings_file() -> None:
    if AppPaths.READY_CODE_SETTINGS_JSON.exists():
        return
    save_json_settings(AppPaths.READY_CODE_SETTINGS_JSON, DEFAULT_READY_CODE_SETTINGS)
