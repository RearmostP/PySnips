"""
PySnips Error & Debug Management System
=======================================
מערכת מרכזית לניהול שגיאות (Errors) וניפוי באגים (Debug) עבור אפליקציית PySnips.

הוראות שימוש חיוניות:
--------------------

1. שימוש בתוך בלוק תפיסת שגיאות (try/except):
   במצב זה חובה להעביר את אובייקט השגיאה (e) כפרמטר `error_obj`.

   >>> try:
   >>>     res = 10 / 0
   >>> except ZeroDivisionError as e:
   >>>     AppErrorHandler.handle_error(
   >>>         error_obj=e,
   >>>         user_message="שגיאה בחישוב הנתונים הגרפיים.",
   >>>         severity="ERROR"
   >>>     )

2. שימוש בתוך בדיקות תנאי לוגיות (if):
   במצב זה אין אובייקט שגיאה, לכן משמיטים את הפרמטר `error_obj`. המערכת תזהה לבד
   את מיקום ה-if ותתעד אותו כ-`LogicalError`.

   >>> if not icon_path.exists():
   >>>     AppErrorHandler.handle_error(
   >>>         user_message="לא הצלחנו לטעון את האייקון של האפליקציה.",
   >>>         dev_message=f"הקובץ חסר בנתיב: {icon_path}",
   >>>         severity="WARNING"
   >>>     )

3. שליטה מתקדמת בערוצי הפלט (דגלים):
   ניתן לכבות או להדליק באופן דינמי את ערוצי הפלט (טרמינל, לוג, חלון גרפי) באמצעות דגלים בוליאנים.

   >>> AppErrorHandler.handle_error(
   >>>     user_message="שגיאת רקע שקטה",
   >>>     show_gui=False,       # לא יקפיץ חלון למשתמש
   >>>     show_terminal=False   # לא ידפיס לטרמינל (יירשם רק בקובץ הלוג)
   >>> )

4. שימוש במערכת ה-Debug (ניפוי באגים):
   הודעות אלו מיועדות למעקב פיתוח רגיל. הן יודפסו ויירשמו לקובץ הלוג המיוחד `pysnips_debug.log`
   רק אם האפליקציה הורצה עם הדגל: `python main.py --debug`. ברצה רגילה הן יהיו רדומות לחלוטין.

   >>> AppDebugger.log("מתחיל לטעון את רכיבי המערכת הדינמיים...")

נתיבי קבצי הלוג:
--------------
- שגיאות קריטיות:  logs/pysnips.log
- הודעות דבאג:      logs/pysnips_debug.log
"""


import sys
import traceback
from pathlib import Path
import datetime
from PySide6.QtWidgets import QMessageBox, QApplication

from core.common.app_paths import AppPaths

# הגדרת נתיבי קבצי הלוג של האפליקציה

ERROR_LOG_PATH = AppPaths.LOGS_DIR / "pysnips.log"
DEBUG_LOG_PATH = AppPaths.LOGS_DIR / "pysnips_debug.log"



class AppErrorHandler:
    """M1: מערכת לניהול שגיאות גמישה - מאפשרת כיבוי/הדלקה של ערוצים והודעות מופרדות"""

    @classmethod
    def handle_error(
            cls,
            user_message: str,  # הודעת המשתמש - פרמטר ראשון (חובה)
            error_obj: Exception = None,  # אובייקט השגיאה (אופציונלי)
            dev_message: str = "",
            severity: str = "ERROR",
            solution_hint: str = "",
            show_terminal: bool = True,
            show_log: bool = True,
            show_gui: bool = True
    ):
        """
        מנהל השגיאות המרכזי - תומך גם בבלוק except וגם בבדיקות if ידניות.
        """
        # 1. חילוץ דינמי של מקור השגיאה
        if error_obj and error_obj.__traceback__:
            # אם יש אובייקט שגיאה אמיתי - נחלץ את נקודת הכשל המקורית שלו
            tb = error_obj.__traceback__
            summary = traceback.extract_tb(tb)
            last_frame = summary[-1] if summary else None
        else:
            # 💡 אם זו בדיקת if ידנית - נבדוק מי קרא ל-handle_error ברגע זה!
            summary = traceback.extract_stack()
            # summary[-2] לוקח אותנו צעד אחד אחורה, אל השורה שבה כתבת את ה-if
            last_frame = summary[-2] if len(summary) >= 2 else None

        if last_frame:
            error_context = {
                "filename": Path(last_frame.filename).name,
                "line": last_frame.lineno,
                "function": last_frame.name
            }
        else:
            error_context = {"filename": "Unknown", "line": 0, "function": "Unknown"}

        # קביעת שם השגיאה הטכנית להצגה
        error_name = type(error_obj).__name__ if error_obj else "LogicalError"
        error_details = str(error_obj) if error_obj else "בדיקת תנאי ידנית בקוד (תנאי נכשל)"

        # התיקון החסר: יצירת המשתנה עבור הודעת הפיתוח
        final_dev_message = dev_message if dev_message else user_message

        # 2. הפעלה מותנית (Conditional) של הערוצים לפי הדגלים
        if show_terminal:
            cls._print_to_terminal(error_context, error_obj, final_dev_message, severity)
        if show_log:
            cls._write_to_log(error_context, error_obj, final_dev_message, severity)
        if show_gui:
            cls._show_gui_dialog(user_message, error_obj, severity, solution_hint)

    @staticmethod
    def _print_to_terminal(context: dict, error_obj: Exception, user_message: str, severity: str):
        """מדפיסה תבנית מעוצבת לטרמינל - קווי קישוט אפורים, קידומות מודגשות"""

        # 🎨 קודי עיצוב וצבעים
        RESET = "\033[0m"
        BOLD = "\033[1m"
        GRAY = "\033[90m"  # צבע אפור עבור קווי הקישוט

        # התאמת אייקון וצבע רק עבור שורת החומרה (Severity)
        if severity == "CRITICAL":
            COLOR_SEV = "\033[95m"  # סגול מודגש
            icon = "🔥"
        elif severity == "ERROR":
            COLOR_SEV = "\033[91m"  # אדום
            icon = "❌"
        elif severity == "WARNING":
            COLOR_SEV = "\033[93m"  # צהוב
            icon = "⚠️"
        else:
            COLOR_SEV = "\033[94m"  # כחול
            icon = "ℹ️"

        # קביעת שם השגיאה והפרטים להדפסה
        error_name = type(error_obj).__name__ if error_obj else "LogicalError"
        error_details = str(error_obj) if error_obj else "None"

        # 🖨️ הדפסת הבלוק המעוצב שלך
        print(f"\n{icon} {GRAY}{'=' * 30} [App Error] {'=' * 30}{RESET} {icon}")
        print(f" {COLOR_SEV}{BOLD}[{severity}]{RESET}")
        print(f" {BOLD}[SYSTEM MESSAGE]{RESET} {user_message}")
        print(f" {BOLD}[The error]{RESET}  {error_name}: {error_details}")
        print(
            f" {BOLD}[Error location]{RESET} `{context['filename']}` -> line {context['line']} -> function `{context['function']}`")
        print(f"{icon} {GRAY}{'=' * 73}{RESET} {icon}\n")

    @staticmethod
    def _write_to_log(context: dict, error_obj: Exception, user_message: str, severity: str):
        """כותבת את השגיאה בצורה מרווחת, קריאה ומיושרת לקובץ הלוג"""

        # 1. השגת הזמן הנוכחי בפורמט נקי
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 2. חילוץ פרטי השגיאה
        error_name = type(error_obj).__name__ if error_obj else "LogicalError"
        error_details = str(error_obj) if error_obj else "None"

        # 3. בניית הבלוק המעוצב של הלוג (עם שורות חדשות \n)
        log_block = (
            f"============================== [App Error] ==============================\n"
            f" [{current_time}] [{severity}]\n"
            f" [SYSTEM MESSAGE] {user_message}\n"
            f" [The error]      {error_name}: {error_details}\n"
            f" [Error location] `{context['filename']}` -> line {context['line']} -> function `{context['function']}`\n"
            f"=========================================================================\n\n"
        )

        # 4. כתיבה (append) בפועל לקובץ הלוג
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(log_block)
        except Exception as e:
            # הגנה מפני קריסה במקרה שהקובץ נעול
            print(f"⚠️ לא ניתן לכתוב לקובץ הלוג: {e}")

    @staticmethod
    def _show_gui_dialog(user_message: str, error_obj: Exception, severity: str, solution_hint: str):
        """מציגה חלון QMessageBox מעוצב למשתמש (רק אם הממשק הגרפי רץ)"""
        if not QApplication.instance():
            return  # מונע קריסה אם ה-GUI עוד לא באוויר

        msg_box = QMessageBox()
        msg_box.setWindowTitle("הודעת מערכת - PySnips")
        msg_box.setText(f"<h3>{user_message}</h3>")

        # קביעת האייקון לפי רמת החומרה
        if severity == "WARNING":
            msg_box.setIcon(QMessageBox.Warning)
        else:
            msg_box.setIcon(QMessageBox.Critical)

        # בניית הפירוט הטכני המורחב (המשתמש יראה בלחיצה על "Show Details")
        detailed_text = (
            f"סוג השגיאה: {type(error_obj).__name__}\n"
            f"תיאור טכני: {error_obj}\n\n"
        )
        if solution_hint:
            detailed_text += f"💡 כיצד לתקן:\n{solution_hint}\n\n"

        detailed_text += f" פרטים מלאים נשמרו בנתיב: {ERROR_LOG_PATH}"

        msg_box.setDetailedText(detailed_text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()


class AppDebugger:
    """M2: מערכת ניפוי באגים (Debug) - פועלת רק אם האפליקציה הורצה עם הדגל --debug"""

    # בדיקה דינמית: האם המתכנת הריץ את התוכנה עם הדגל מבוקש?
    IS_DEBUG_MODE = "--debug" in sys.argv

    @classmethod
    def log(cls, message: str):
        """
        מדפיס הודעת מעקב לטרמינל ורושם אותה לקובץ לוג ייעודי.
        אם התוכנה לא רצה במצב דבאג - הפונקציה לא עושה כלום (רדומה).
        """
        if not cls.IS_DEBUG_MODE:
            return  # יציאה שקטה, מצב דבאג כבוי

        # שימוש ב-traceback כדי לדעת מי קרא לפונקציית הלוג (שלב 1 אחורה במחסנית)
        # אנחנו לוקחים את ה-Stack הנוכחי כדי לדעת איפה המתכנת שם את ה-AppDebugger.log
        summary = traceback.extract_stack()
        if len(summary) >= 2:
            caller_frame = summary[-2]  # הצעד שקרא ל-log()
            filename = Path(caller_frame.filename).name
            line = caller_frame.lineno
        else:
            filename, line = "Unknown", 0

        formatted_msg = f"[DEBUG] ({filename}:{line}) -> {message}"

        # 1. הדפסה ישירה למסך המתכנת
        print(formatted_msg)

        # 2. כתיבה לקובץ לוג נפרד של דבאג
        try:
            with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(formatted_msg + "\n")
        except Exception:
            pass  # הגנה מפני קריסה של הדבאגר עצמו