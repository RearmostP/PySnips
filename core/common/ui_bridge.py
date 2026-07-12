"""
פילוסופיית המערכת: גשר ממשק-לוגיקה (UI-Logic Bridge)
------------------------------------------------------------
מערכת זו משמשת כגשר בין קבצי עיצוב (.ui) לבין הלוגיקה של האפליקציה.

1. לוגיקה מול תצוגה: הקוד הלוגי (BaseLogicController) מופרד לחלוטין מהתצוגה הויזואלית.
   הוא אינו "יורש" מהמסך, אלא "מחזיק" אותו (Composition).

2. חסינות (Robustness): שימוש ב-Safe Binding. אם משתמש מחליף קובץ UI ומשמיט רכיבים,
   האפליקציה תדלג על החיבור הלוגי במקום לקרוס.

3. גמישות: המערכת מאפשרת טעינה דינמית של קבצי XML (.ui) בזמן ריצה, מה שמאפשר
   החלפת "סקינים" או שינוי פריסת כפתורים ללא נגיעה בקוד המקור.
"""

import sys
import xml.etree.ElementTree as ET
from PySide6.QtWidgets import QWidget, QDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, Qt 

from core.common.error_manager import AppErrorHandler, AppDebugger
from core.common.app_paths import AppPaths # Added this import


class _UiLoader(QUiLoader):
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


"""
הוראות שימוש ל-BaseLogicController:
---------------------------------
1. ירושה: צור מחלקה חדשה עבור הלוגיקה של המסך שיורשת מ-BaseLogicController.
2. אתחול נתונים (init_data): דרוס פונקציה זו כדי להגדיר משתנים, רשימות או טעינה מה-DB.
   היא רצה ראשונה כדי להבטיח שהמידע מוכן לפני שהמידע מוכן לפני שהמשתמש יוכל ללחוץ על משהו.
3. חיבור לוגיקה (setup_logic): דרוס פונקציה זו כדי לחבר כפתורים וסיגנלים מה-UI.
   מומלץ להשתמש ב-safe_connect כדי למנוע קריסות אם הממשק ישתנה בעתיד.
4. הפעלה: צור מופע (Instance) של מחלקת הלוגיקה והעבר לו את ה-View שנוצר.

דוגמה מהירה:
    class MyLogic(BaseLogicController):
        def init_data(self):
            self.items = ["שליף 1", "שליף 2"]
        
        def setup_logic(self):
            self.safe_connect("btn_save", "clicked", self.save_action)
"""
class BaseLogicController: 
    """
    מחלקה בסיסית לכל מחלקות הלוגיקה.
    היא מחזיקה את ה-UI כאובייקט נפרד ומאפשרת חיבור בטוח של רכיבים.
    """
    def __init__(self, view: QWidget):
        self.view = view
        self.init_data()    # 1. קודם כל מכינים את הנתונים והמשתנים
        self.setup_logic()  # 2. אחר כך מחברים אותם לכפתורים ב-UI

    def init_data(self):
        """לדריסה במחלקות היורשות - כאן מגדירים משתנים וטוענים נתונים ראשוניים"""
        pass

    def setup_logic(self):
        """לדריסה במחלקות היורשות - כאן מחברים סיגנלים (כפתורים וכו')"""
        # דוגמה: self.safe_connect("btn_save", "clicked", self.on_save_clicked)
        pass

    def get_widget(self, name: str):
        """
        מחזיר ווידג'ט לפי שם בצורה בטוחה. 
        אם המשתמש מחק את הווידג'ט מה-UI, האפליקציה לא תקרוס.
        """
        widget = getattr(self.view, name, None)
        if not widget:
            AppDebugger.log(f" אזהרה: הווידג'ט '{name}' לא נמצא בממשק (UI). הלוגיקה עבורו לא תחובר.")
        return widget

    def safe_connect(self, widget_name: str, signal_name: str, slot_func):
        """חיבור בטוח של סיגנל לפונקציה"""
        widget = self.get_widget(widget_name)
        if widget:
            signal = getattr(widget, signal_name, None)
            if signal:
                signal.connect(slot_func)
                return True
        return False


# Removed DraggableDialog class


def get_ui_root_class(ui_filename: str) -> type:
    """
    פונקציית עזר שקוראת את ה-XML של ה-UI ומזהה האם רכיב השורש
    הוא QDialog, QWidget או QMainWindow ומחזירה את ה-Class המתאים של PySide6.
    """
    ui_path = AppPaths.UI_DIR / ui_filename
    if not ui_path.exists():
        return QWidget  # Fallback דיפולטיבי, השגיאה האמיתית תטופל בהמשך בטעינה

    try:
        tree = ET.parse(ui_path)
        root = tree.getroot()
        widget_element = root.find("widget")
        if widget_element is not None:
            ui_class_name = widget_element.get("class")
            if ui_class_name == "QDialog":
                return QDialog # Reverted to QDialog
    except Exception:
        pass

    return QWidget  # ברירת מחדל עבור כל השאר


def create_view_class(ui_filename: str):
    """
    מפעל מחלקות (Factory) שמחזיר קלאס בסיס מותאם אישית דינמית.
    מייצר מופע של View שמוכן להזרקה לתוך Controller.
    """
    base_class = get_ui_root_class(ui_filename)

    class DynamicView(base_class):
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
            AppDebugger.log(f" מערכת הגשר: מפענחת את תצוגת המשתמש '{display_path}'...")

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
                loader = _UiLoader(self)
                loader.load(ui_file)
                ui_file.close()

                AppDebugger.log(f" מערכת הגשר: התצוגה '{display_path}' חוברה בהצלחה (סוג: {base_class.__name__}).")

            except Exception as e:
                AppErrorHandler.handle_error(
                    error_obj=e,
                    user_message="קריסה קריטית בזמן פענוח ממשק המשתמש (UI Parsing Error).",
                    severity="CRITICAL"
                )
                sys.exit(1)

    return DynamicView