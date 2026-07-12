"""
PySnips Error & Debug Management System
=======================================
מערכת מרכזית לניהול שגיאות (Errors) וניפוי באגים (Debug) עבור אפליקציית PySnips.
"""

import sys
import inspect
import os
import re
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
            # אם זו בדיקת if ידנית - נבדוק מי קרא ל-handle_error ברגע זה
            summary = traceback.extract_stack()
            last_frame = summary[-2] if len(summary) >= 2 else None

        if last_frame:
            error_context = {
                "filename": Path(last_frame.filename).name,
                "line": last_frame.lineno,
                "function": last_frame.name
            }
        else:
            error_context = {"filename": "Unknown", "line": 0, "function": "Unknown"}

        # הגדרת הודעת הפיתוח הסופית
        final_dev_message = dev_message if dev_message else user_message

        # 2. הפעלה מותנית של הערוצים לפי הדגלים (העברת final_dev_message במקום user_message)
        if show_terminal:
            cls._print_to_terminal(error_context, error_obj, final_dev_message, severity)
        if show_log:
            cls._write_to_log(error_context, error_obj, final_dev_message, severity)
        if show_gui:
            cls._show_gui_dialog(user_message, error_obj, severity, solution_hint)

    @staticmethod
    def _print_to_terminal(context: dict, error_obj: Exception, dev_message: str, severity: str):
        """מדפיסה תבנית מעוצבת לטרמינל - קווי קישוט אפורים, קידומות מודגשות"""
        RESET = "\033[0m"
        BOLD = "\033[1m"
        GRAY = "\033[90m"

        if severity == "CRITICAL":
            COLOR_SEV = "\033[95m"
            icon = "🔥"
        elif severity == "ERROR":
            COLOR_SEV = "\033[91m"
            icon = "❌"
        elif severity == "WARNING":
            COLOR_SEV = "\033[93m"
            icon = "⚠️"
        else:
            COLOR_SEV = "\033[94m"
            icon = "ℹ️"

        error_name = type(error_obj).__name__ if error_obj else "LogicalError"
        error_details = str(error_obj) if error_obj else "בדיקת תנאי ידנית בקוד (תנאי נכשל)"

        print(f"\n{icon} {GRAY}{'=' * 30} [App Error] {'=' * 30}{RESET} {icon}")
        print(f" {COLOR_SEV}{BOLD}[{severity}]{RESET}")
        print(f" {BOLD}[SYSTEM MESSAGE]{RESET} {dev_message}")
        print(f" {BOLD}[The error]{RESET}  {error_name}: {error_details}")
        print(f" {BOLD}[Error location]{RESET} `{context['filename']}` -> line {context['line']} -> function `{context['function']}`")
        print(f"{icon} {GRAY}{'=' * 73}{RESET} {icon}\n")

    @staticmethod
    def _write_to_log(context: dict, error_obj: Exception, dev_message: str, severity: str):
        """כותבת את השגיאה בצורה מרווחת, קריאה ומיושרת לקובץ הלוג"""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        error_name = type(error_obj).__name__ if error_obj else "LogicalError"
        error_details = str(error_obj) if error_obj else "None"

        log_block = (
            f"============================== [App Error] ==============================\n"
            f" [{current_time}] [{severity}]\n"
            f" [SYSTEM MESSAGE] {dev_message}\n"
            f" [The error]      {error_name}: {error_details}\n"
            f" [Error location] `{context['filename']}` -> line {context['line']} -> function `{context['function']}`\n"
            f"=========================================================================\n\n"
        )

        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(log_block)
        except Exception as e:
            print(f"⚠️ לא ניתן לכתוב לקובץ הלוג: {e}")

    @staticmethod
    def _show_gui_dialog(user_message: str, error_obj: Exception, severity: str, solution_hint: str):
        """מציגה חלון QMessageBox מעוצב למשתמש (בטוח לשימוש גם ללא אובייקט שגיאה)"""
        if not QApplication.instance():
            return

        msg_box = QMessageBox()
        msg_box.setWindowTitle("הודעת מערכת - PySnips")
        msg_box.setText(f"<h3>{user_message}</h3>")

        if severity == "WARNING":
            msg_box.setIcon(QMessageBox.Warning)
        else:
            msg_box.setIcon(QMessageBox.Critical)

        # תיקון בטיחות: מניעת קריסה כאשר error_obj הוא None
        error_name = type(error_obj).__name__ if error_obj else "LogicalError"
        error_details = str(error_obj) if error_obj else "לא זוהה אובייקט חריגה פיזי (בדיקת תנאי לוגית)"

        detailed_text = (
            f"סוג השגיאה: {error_name}\n"
            f"תיאור טכני: {error_details}\n\n"
        )
        if solution_hint:
            detailed_text += f"💡 כיצד לתקן:\n{solution_hint}\n\n"

        detailed_text += f" פרטים מלאים נשמרו בנתיב: {ERROR_LOG_PATH}"

        msg_box.setDetailedText(detailed_text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()


class AppDebugger:
    @staticmethod
    def log(message: str):
        # תיקון: הבדיקה מוקמת בראש הפונקציה למניעת הרצת קוד מיותרת
        if "--debug" not in sys.argv:
            return

        frame = inspect.stack()[1]
        filename = os.path.basename(frame.filename)
        line_number = frame.lineno

        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        CYAN = "\033[96m"
        GRAY = "\033[90m"
        WHITE = "\033[37m"
        RESET = "\033[0m"

        path_pattern = r"['\"]([^'\"]+\.(?:ui|py))['\"]"
        if re.search(path_pattern, message):
            message = re.sub(path_pattern, r"root:\1", message)
            message = re.sub(r"(root:[^\s]+)", f"{CYAN}\\1{RESET}", message)

        raw_location = f"({filename}:{line_number})"
        colored_location = (
            f"{GRAY}({YELLOW}{filename}:{line_number}{GRAY})"
            f"{RESET}{' ' * (26 - len(raw_location))}"
        )

        log_prefix = f"{GREEN}[DEBUG]{RESET}"
        arrow = f"{WHITE}->{RESET}"

        print(f"{log_prefix} {colored_location} {arrow} {message}")