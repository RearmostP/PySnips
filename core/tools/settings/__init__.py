# תפקיד הקובץ:
# נקודת ייצוא נוחה לכלי ההגדרות.
# מאפשר לייבא פונקציות ומחלקות מרכזיות של מערכת ההגדרות ממקום אחד.

from core.tools.settings.snips_settings import (
    DEFAULT_TRASH_RETENTION_DAYS,
    SnipsSettings,
    SnipsTrashSettings,
    load_snips_settings,
    load_snips_trash_settings,
    save_snips_settings,
    save_snips_trash_settings,
)
from core.tools.settings.settings_bootstrap import ensure_settings_files_exist
