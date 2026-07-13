import sys
import xml.etree.ElementTree as ET
from PySide6.QtWidgets import QWidget, QDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice

from core.tools.common.error_manager import AppErrorHandler, AppDebugger
from core.tools.common.app_paths import AppPaths


class UiLoader(QUiLoader):
    """
    מחלקה פנימית שיוצרת את הרכיב על גבי ה-instance הקיים
    במקום לייצר Widget חדש ומנותק בזיכרון.
    """

    def __init__(self, baseinstance):
        super().__init__()
        self.baseinstance = baseinstance

    def createWidget(self, class_name, parent=None, name=""):
        if parent is None and self.baseinstance:
            return self.baseinstance
        return super().createWidget(class_name, parent, name)


def get_ui_root_class(ui_filename: str) -> type:
    """
    פונקציית עזר שקוראת את ה-XML של ה-UI ומזהה האם רכיב השורש
    הוא QDialog, QWidget או QMainWindow ומחזירה את ה-Class המתאים של PySide6.
    """
    ui_path = AppPaths.UI_DIR / ui_filename
    if not ui_path.exists():
        AppErrorHandler.handle_error(
            user_message=f"קובץ ממשק המשתמש '{ui_filename}' לא נמצא.",
            dev_message=f"לא ניתן למצוא את הקובץ בנתיב: {ui_path}",
            severity="CRITICAL",
            show_gui=True
        )
        sys.exit(1)

    try:
        tree = ET.parse(ui_path)
        root = tree.getroot()
        widget_element = root.find("widget")
        if widget_element is not None:
            ui_class_name = widget_element.get("class")
            if ui_class_name == "QDialog":
                return QDialog
    except Exception:
        pass

    return QWidget  # ברירת מחדל עבור כל השאר


def create_dynamic_ui_loader(ui_filename: str):
    """
    מפעל מחלקות (Factory) שמחזיר קלאס בסיס מותאם אישית דינמית.
    מוודא שהלודר יירש מהמחלקה הנכונה (QWidget או QDialog).
    """
    base_class = get_ui_root_class(ui_filename)

    class DynamicUiLoader(base_class):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.ui_filename = ui_filename
            self._load_ui_dynamically()

        def _load_ui_dynamically(self):
            """טוען את קובץ ה-UI בזמן ריצה וממפה את הרכיבים שלו"""
            ui_path = AppPaths.UI_DIR / self.ui_filename

            # 1. חישוב הנתיב היחסי כבר בהתחלה לצורך לוגים נקיים
            try:
                display_path = ui_path.relative_to(AppPaths.PROJECT_DIR)
            except ValueError:
                display_path = self.ui_filename

            # תיקון הלוג הראשון: הדפסת נתיב קצר
            AppDebugger.log(f" לודר אוניברסלי: מזהה ומפענח את המסך '{display_path}'...")

            if not ui_path.exists():
                AppErrorHandler.handle_error(
                    user_message=f"מסך המערכת '{display_path}' לא נמצא.",
                    dev_message=f"לא ניתן למצוא את הקובץ בנתיב: {ui_path}",
                    severity="CRITICAL",
                    show_gui=True
                )
                sys.exit(1)

            ui_file = QFile(str(ui_path))
            if not ui_file.open(QIODevice.ReadOnly):
                AppErrorHandler.handle_error(
                    user_message="נכשלה פתיחת קובץ ממשק המשתמש.",
                    dev_message=f"לא ניתן לפתוח את הקובץ {ui_path} לקריאה.",
                    severity="ERROR"
                )
                sys.exit(1)

            try:
                loader = UiLoader(self)
                loader.load(ui_file)
                ui_file.close()

                # תיקון הלוג השני: הדפסת נתיב קצר
                AppDebugger.log(f" לודר אוניברסלי: '{display_path}' נטען בהצלחה (סוג: {base_class.__name__}).")

            except Exception as e:
                AppErrorHandler.handle_error(
                    error_obj=e,
                    user_message="קריסה קריטית בזמן פענוח ממשק המשתמש (UI Parsing Error).",
                    severity="CRITICAL"
                )
                sys.exit(1)

    return DynamicUiLoader