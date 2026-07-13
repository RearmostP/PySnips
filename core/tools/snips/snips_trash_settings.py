# תפקיד הקובץ:
# שכבת תאימות זמנית לייבוא הישן של הגדרות אשפת השליפים.
# הלוגיקה האמיתית עברה ל-core.tools.settings.snips_settings, והקובץ הזה נשאר
# כדי שקוד ישן שעדיין מייבא ממנו לא יישבר.

from core.tools.settings.snips_settings import (
    DEFAULT_TRASH_RETENTION_DAYS,
    SnipsTrashSettings,
    load_snips_trash_settings,
    save_snips_trash_settings,
)
