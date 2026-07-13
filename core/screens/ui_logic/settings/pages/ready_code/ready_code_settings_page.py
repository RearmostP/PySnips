# תפקיד הקובץ:
# לוגיקת עמוד ההגדרות של קוד מוכן.
# כרגע העמוד משמש כשלד לעתיד, ומופרד כדי שהגדרות קוד מוכן לא יעמיסו
# על חלון ההגדרות הראשי.

from PySide6.QtWidgets import QWidget

from core.tools.common.app_paths import AppPaths
from core.tools.common.dynamic_ui_loader import create_dynamic_ui_loader


class ReadyCodeSettingsPage(create_dynamic_ui_loader(AppPaths.READY_CODE_SETTINGS_PAGE)):
    def get_view(self) -> QWidget:
        return self
