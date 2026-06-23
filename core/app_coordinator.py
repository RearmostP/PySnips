import sys
from core.common.screen_manager import ScreenManager
from core.screens.ui_logic.home.home_screen import HomeScreen
from core.screens.ui_logic.snips.snippets_screen import SnippetsScreen
from core.screens.ui_logic.snips.create_snip_dialog import CreateSnipDialog

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

    def _route_to_ready_code(self):
        AppDebugger.log("נתב מרכזי: מעביר שליטה ל-ReadyCodeFlow.")
        flow = ReadyCodeFlow(self.screen_manager)
        flow.start()


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
            snippets_screen.btn_new_snip.clicked.connect(self._handle_new_snippet_dialog)

            # רישום אקטיבי - רק עכשיו הוא נכנס ל-ScreenManager
            self.screen_manager.register_screen("snippets", snippets_screen)

        # 2. רק אחרי שהמסך בוודאות רשום ומיוצר, מבצעים את המעבר הפיזי!
        self.screen_manager.switch_to("snippets")
        AppDebugger.log("SnippetsFlow: המעבר למסך השליפים בוצע בהצלחה.")

    def _handle_new_snippet_dialog(self):
        """טעינה והצגה מודאלית של דיאלוג יצירת שליף חדש"""
        AppDebugger.log("SnippetsFlow: המשתמש ביקש ליצור שליף. מציג דיאלוג...")
        dialog = CreateSnipDialog(parent=self.screen_manager)
        dialog.exec()


class ReadyCodeFlow:
    """מחלקה עצמאית שמנהלת את סדר הפעולות והלוגיקה של מסך קוד מוכן"""

    def __init__(self, screen_manager):
        self.screen_manager = screen_manager

    def start(self):
        AppDebugger.log("ReadyCodeFlow: מתחיל סדר פעולות עבור מסך קוד מוכן...")
        # כאן תבוא הלוגיקה הבאה של מסך הקוד המוכן כשתבנה אותו
        self.screen_manager.switch_to("ready_code")


