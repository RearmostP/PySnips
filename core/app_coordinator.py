import sys

from core.common.screen_manager import ScreenManager

from core.screens.ui_logic.home.home_screen import HomeScreen
from core.screens.ui_logic.snips.snippets_screen import SnippetsScreen
from core.screens.ui_logic.snips.create_snips_dialog import CreateSnipsDialog

from core.common.error_manager import AppDebugger
from core.boot import run_startup_checks

class AppCoordinator:
    """
    Orchestrator - מנהל על של האפליקציה.
    מבצע בדיקות, מציג את מסך הבית ומנתב את השליטה ל-Flow המתאים.
    """

    def __init__(self):
        self.screen_manager = None

    def start(self):
        """נקודת ההפעלה המרכזית מה-main"""
        # 1. הרצת בדיקות השלמות תחילה
        if not run_startup_checks():
            AppDebugger.log("בדיקות השלמות נכשלו. הריצה הסתיימה.")
            sys.exit(1)

        AppDebugger.log("בדיקות השלמות עברו בהצלחה. מתחיל אתחול...")

        # 2. יצירת מנהל המסכים
        self.screen_manager = ScreenManager()

        # 3. טעינה מיידית של מסך הבית
        self._load_home_screen()

    def _load_home_screen(self):
        """טוען ומציג את מסך הבית ומחבר את הנתב המרכזי לכפתורים שלו"""
        AppDebugger.log("מזהה ומפעיל טעינה עבור מסך הבית בלבד [home]...")

        home_screen = HomeScreen(parent=self.screen_manager)
        self.screen_manager.register_screen("home", home_screen)

        # חיבור כפתורי הניווט הראשיים לנתבים הפנימיים
        home_screen.btn_go_snippets.clicked.connect(self._route_to_snippets)
        home_screen.btn_go_ready_code.clicked.connect(self._route_to_ready_code)

        # הצגת האפליקציה
        self.screen_manager.switch_to("home")
        self.screen_manager.resize(900, 650)
        self.screen_manager.show()

        AppDebugger.log("מסך הבית נטען בהצלחה. המערכת ממתינה לבחירת המשתמש.")

    def _route_to_snippets(self):
        AppDebugger.log("נתב מרכזי: מעביר שליטה ל-SnippetsFlow.")
        flow = SnippetsFlow(self.screen_manager)
        flow.start()

        # חבר את כפתור יצירת השליף לפותח הדיאלוג ברמת ה-Coordinator
        snippets_screen = self.screen_manager._screens.get("snippets")
        if snippets_screen:
   
            snippets_screen.btn_new_snippet.clicked.connect(self._open_create_snips_dialog)

    def _route_to_ready_code(self):
        AppDebugger.log("נתב מרכזי: מעביר שליטה ל-ReadyCodeFlow.")
        flow = ReadyCodeFlow(self.screen_manager)
        flow.start()

    def _open_create_snips_dialog(self):
        """Helper on the coordinator to open the CreateSnips dialog via flow."""
        flow = CreateSnipsFlow(self.screen_manager)
        flow.start()

#-----------------------------------------------------------------------------

class CreateSnipsFlow:
    """Flow לטיפול בדיאלוג יצירת שליף"""

    def __init__(self, screen_manager):
        self.screen_manager = screen_manager
        self.dialog = CreateSnipsDialog(parent=self.screen_manager)

    def start(self):

        AppDebugger.log("CreateSnipsFlow: מציג דיאלוג יצירת שליף...")

        # מרכז הדיאלוג ביחס למסך 'snippets' אם קיים, אחרת ביחס ל-screen_manager
        parent_widget = self.screen_manager._screens.get("snippets", self.screen_manager)

        # מיקום: מרכז אופקי, ו-40px מתחת לשפת החלון העליונה של האפליקציה — כמו בתמונה
        center_x = parent_widget.x() + (parent_widget.width() - self.dialog.width()) // 2
        top_y = parent_widget.y() + 40
        self.dialog.move(center_x, top_y)

        self.dialog.setup_events()
        self.dialog.exec()


#----------------------------------------------------------------------------------------------------

class SnippetsFlow:
    """מחלקה עצמאית שמנהלת את סדר הפעולות והלוגיקה של מסך השליפים"""

    def __init__(self, screen_manager):
        self.screen_manager = screen_manager

    def start(self):
        AppDebugger.log("SnippetsFlow: מתחיל סדר פעולות עבור מסך השליפים...")

        # גישה ישירה למילון ה-screens כדי לבדוק קיום בשקט בלי לעורר שגיאות ב-ScreenManager

        if not self.screen_manager.has_screen("snippets"):
            AppDebugger.log("SnippetsFlow: מסך השליפים לא קיים בזיכרון. מפעיל טעינה ראשונית...")
            snippets_screen = SnippetsScreen(parent=self.screen_manager)

            # חיבור אירועים ורכיבים
            snippets_screen.setup_events()

            # רישום אקטיבי - רק עכשיו הוא נכנס ל-ScreenManager
            self.screen_manager.register_screen("snippets", snippets_screen)

        # 2. רק אחרי שהמסך בוודאות רשום ומיוצר, מבצעים את המעבר הפיזי!
        self.screen_manager.switch_to("snippets")
        AppDebugger.log("SnippetsFlow: המעבר למסך השליפים בוצע בהצלחה.")

    def _open_create_snips_dialog(self):
        # פונה ל-CreateSnipsFlow כדי להציג את הדיאלוג
        flow = CreateSnipsFlow(self.screen_manager)
        flow.start()

#----------------------------------------------------------------------------------------

class ReadyCodeFlow:
    """מחלקה עצמאית שמנהלת את סדר הפעולות והלוגיקה של מסך קוד מוכן"""

    def __init__(self, screen_manager):
        self.screen_manager = screen_manager

    def start(self):
        AppDebugger.log("ReadyCodeFlow: מתחיל סדר פעולות עבור מסך קוד מוכן...")
        # כאן תבוא הלוגיקה הבאה של מסך הקוד המוכן כשתבנה אותו
        self.screen_manager.switch_to("ready_code")


