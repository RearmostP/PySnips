# core/common/error_manager.py
"""
⚙️ PySnips 0.3 - Global Error Management System
=================================================

📜 מדריך שימוש וצורת עבודה:
-----------------------------
מערכת זו משמשת כשומר הסף הראשי של האפליקציה מפני קריסות בלתי צפויות.
בסביבות GUI (כמו PySide6), שגיאות קוד שלא טופלו ב-try/except עלולות לגרום
לאפליקציה להיסגר בשבריר שנייה ("להיעלם" מהמסך) בלי להשאיר עקבות למשתמש.

איך המערכת עובדת מאחורי הקלעים?
1. חטיפת שגיאות גלובלית (sys.excepthook): המערכת מחליפה את מנגנון הטיפול
   ברירת המחדל של פייתון. כל שגיאה (Exception) שמתרחשת בכל מקום באפליקציה
   ולא נתפסה באופן מקומי - מנותבת אוטומטית לכאן.

2. מערכת רישום כפולה (Logging Handler):
   - כותבת באופן מיידי את עץ השגיאה המלא (Traceback) לקובץ 'pysnips.log'.
   - מדפיסה למסוף (sys.stdout) הודעה מודגשת ומעוצבת עבור המתכנת ב-PyCharm.

3. חווית משתמש (QMessageBox): אם השגיאה התרחשה בזמן שהממשק הגרפי כבר רץ,
   המערכת תקפיץ חלון אזהרה קריטי רשמי של Qt המודיע למשתמש שהאפליקציה קרסה,
   ומאפשר לו להרחיב את התיאור הטכני ולהעתיק את נתיב קובץ הלוג כדי לשלוח למפתח.

🛠️ הוראות הפעלה באפליקציה:
----------------------------
כדי שהמערכת תגן על כל חלקי התוכנה (כולל שלבי האתחול), יש לקרוא לפונקציה
setup_error_manager() בשורה הראשונה ביותר בתוך קובץ ה-main.py, לפני כל ייבוא
או הפעלה של לוגיקה אחרת.
"""

import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QMessageBox, QApplication

from core.common.app_paths import AppPaths

LOG_FILE_PATH = AppPaths.LOGS_DIR / "pysnips.log"


def setup_error_manager():
    """
    מגדיר את מערכת ניהול השגיאות הגלובלית של האפליקציה.
    חוטף שגיאות לא מטופלות, רושם אותן ללוג ומציג חלון למשתמש.
    """
    # 1. הגדרת מערכת ה-Logging (כותב לקובץ ומדפיס למסוף במקביל)
    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_FILE_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)  # <--- התיקון פה! Stream אחד בלבד
        ]
    )

    # 2. פונקציית החטיפה (Excepthook)
    def global_exception_handler(exctype, value, traceback):
        # הדפסת השגיאה המלאה לתוך קובץ הלוג
        logging.error("קריסת מערכת בלתי צפויה!", exc_info=(exctype, value, traceback))

        # יצירת הודעה מעוצבת ומפורטת עבור המסוף של המתכנת
        print("\n" + "🔥 " * 25)
        print(f"❌ [Error Manager] קריסה קריטית באפליקציה!")
        print(f"   <- סוג השגיאה: {exctype.__name__}")
        print(f"   <- פירוט: {value}")
        print(f"   📂 פרטי הקריסה המלאים נשמרו בנתיב: {LOG_FILE_PATH}")
        print("🔥 " * 25 + "\n")

        # 3. הקפצת חלון התרעה ידידותי למשתמש (רק אם ה-QApplication כבר רץ)
        if QApplication.instance():
            show_error_dialog_to_user(exctype.__name__, str(value))

        # סגירת האפליקציה בצורה בטוחה עם קוד שגיאה 1
        sys.exit(1)

    # הזרקת החוטף הגלובלי לתוך הליבה של פייתון
    sys.excepthook = global_exception_handler
    print("🛡️  Error Manager: מערכת הגנת הקריסות הופעלה בהצלחה.")


def show_error_dialog_to_user(error_type: str, error_message: str, icon_type: str = "critical"):
    """
    מציג חלון הודעה (QMessageBox) מעוצב למשתמש בזמן שגיאה או אזהרה.
    מתאים לשימוש יזום על ידי המתכנת בכל רחבי האפליקציה (למשל ב-try/except).

    💡 כיצד להשתמש בקוד שלך (דוגמה):
    ---------------------------------
    try:
        with open("snips.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        show_error_dialog_to_user(
            error_type="קובץ חסר",
            error_message="לא נפתח קובץ המידע snips.json. האפליקציה תיצור קובץ חדש.",
            icon_type="warning"  # אפשרויות: "critical", "warning", "info"
        )

    📥 פרמטרים:
    -----------
    :param error_type: (str) כותרת משנית/סוג השגיאה (יופיע בתוך הפירוט הטכני).
    :param error_message: (str) תיאור השגיאה בעברית שמסביר למשתמש מה קרה.
    :param icon_type: (str) סוג האייקון שיוצג בחלון. ברירת מחדל היא "critical".
                       אפשרויות:
                       - "critical" (איקס אדום - לשגיאות קורסות)
                       - "warning" (משולש צהוב - לאזהרות או קבצים חסרים)
                       - "info" (עיגול כחול - להודעות מידע רגילות)
    """
    # ודאות שה-QApplication רץ, אחרת לא ניתן להציג חלונות Qt
    if not QApplication.instance():
        print(f"⚠️ [QMessageBox חסום] לא ניתן להציג חלון, QApplication לא באוויר. שגיאה: {error_message}")
        return

    msg_box = QMessageBox()
    msg_box.setWindowTitle("הודעת מערכת - PySnips")
    msg_box.setText("אופס! נתקלנו בבעיה בביצוע הפעולה.")

    # קביעת האייקון בהתאם לבקשת המתכנת
    if icon_type == "warning":
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText("אזהרה במערכת")  # משנה את הטקסט הראשי שיתאים לאזהרה
    elif icon_type == "info":
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("הודעת עדכון")
    else:
        msg_box.setIcon(QMessageBox.Critical)

    # פירוט טכני מורחב שהמשתמש יכול לראות בלחיצה על "Show Details"
    detailed_text = (
        f"סוג האירוע: {error_type}\n"
        f"תיאור: {error_message}\n\n"
        f"📂 במידה ומדובר בקריסה, פרטים מלאים נשמרים ב-pysnips.log"
    )
    msg_box.setDetailedText(detailed_text)

    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec()