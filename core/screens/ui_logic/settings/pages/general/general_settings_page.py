# תפקיד הקובץ:
# לוגיקת עמוד ההגדרות הכלליות.
# כרגע העמוד משמש כשלד לעתיד, ומחזיר את ה-view שלו לחלון ההגדרות הראשי.

from PySide6.QtWidgets import QWidget

from core.tools.common.app_paths import AppPaths
from core.tools.common.dynamic_ui_loader import create_dynamic_ui_loader


class GeneralSettingsPage(create_dynamic_ui_loader(AppPaths.GENERAL_SETTINGS_PAGE)):
    def get_view(self) -> QWidget:
        return self
