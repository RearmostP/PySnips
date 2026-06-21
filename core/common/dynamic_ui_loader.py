import sys
from PySide6.QtWidgets import QWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice

# ייבוא מערכת ניהול השגיאות והדבאג שלנו
from core.common.error_manager import AppErrorHandler, AppDebugger
from core.common.app_paths import AppPaths


class UiLoader(QUiLoader):
    """
    מחלקה פנימית שיוצרת את הרכיב על גבי ה-Widget הקיים
    במקום לייצר Widget חדש ומנותק בזיכרון.
    """

    def __init__(self, baseinstance):
        super().__init__()
        self.baseinstance = baseinstance

    def createWidget(self, class_name, parent=None, name=""):
        if parent is None and self.baseinstance:
            return self.baseinstance
        return super().createWidget(class_name, parent, name)


class DynamicUiLoader(QWidget):
    """
    מחלקת בסיס לכל המסכים באפליקציה (Home, Snippets, NewSnippet).
    כל מסך יירש ממנה ויקבל טעינה דינמית אוטומטית וממוגנת שגיאות.
    """

    def __init__(self, ui_file_name: str, parent=None):
        super().__init__(parent)
        self.ui_filename = ui_file_name
        self._load_ui_dynamically()


    def _load_ui_dynamically(self):
        """טוען את קובץ ה-UI בזמן ריצה וממפה את הרכיבים שלו"""
        # 1. בניית הנתיב המלא לקובץ ה-UI
        ui_path = AppPaths.UI_DIR / self.ui_filename

        AppDebugger.log(f"מנסה לטעון באופן דינמי את המסך: {self.ui_filename}")

        # 2. בדיקת הגנה ידנית (if) - האם הקובץ בכלל קיים על הדיסק?
        if not ui_path.exists():
            AppErrorHandler.handle_error(
                user_message=f"מסך המערכת '{self.ui_filename}' לא נמצא.",
                dev_message=(f"""לא ניתן למצוא את הקובץ בנתיב: {ui_path}
                  הסיבה לכך היא או שהקובץ פיזית חסר בדיסק, או שהעברת שם קובץ שגוי/לא קיים
                  בתוך ה-super().__init__ של המחלקה היורשת ({self.__class__.__name__})"""),
                severity="CRITICAL",
                solution_hint="וודא שלא מחקת את הקובץ מתיקיית core/ui או שלא שינית לו את השם בטעות.",
                show_gui=True
            )
            sys.exit(1)

        # 3. ניסיון פתיחה וטעינה של הקובץ (try/except)
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QIODevice.ReadOnly):
            AppErrorHandler.handle_error(
                user_message="נכשלה פתיחת קובץ ממשק המשתמש.",
                dev_message=f"לא ניתן לפתוח את הקובץ {ui_path} לקריאה (QFile failure).",
                severity="ERROR"
            )
            sys.exit(1)

        try:
            # שימוש ב-Loader המותאם כדי להזריק את ה-UI ישירות לתוך ה-class שלנו (self)
            loader = UiLoader(self)
            loader.load(ui_file)
            ui_file.close()

            AppDebugger.log(f" קובץ ה-UI '{self.ui_filename}' נטען בהצלחה לזיכרון.")

        except Exception as e:
            # תפיסת שגיאות קריסה בזמן טעינת ה-XML (למשל אם קובץ ה-UI הושחת או נקטע)
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="קריסה קריטית בזמן פענוח ממשק המשתמש (UI Parsing Error).",
                severity="CRITICAL",
                solution_hint="ייתכן שקובץ ה-UI נשמר בצורה לא תקינה בדיזיינר. נסה לפתוח ולשמור אותו מחדש."
            )
            sys.exit(1)