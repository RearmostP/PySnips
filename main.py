# main.py
"""
📌 PySnips 0.4 - Main Application Entry Point & Project Guide
==============================================================

👋 ברוך הבא למפתח! קובץ זה הוא שער הכניסה הראשי של האפליקציה.
לפני שאתה צולל אל הקוד, אנא קרא את ספר החוקים ומפת הקבצים של הפרויקט.

📋 ספר החוקים לשמות ווידג'טים (Naming Conventions Policy):
-----------------------------------------------------------
המערכת אוכפת חוקיות שמות נוקשה ב-Qt Designer כדי למנוע קוד מפוזר ומבולגן.
1. חובה להשתמש בקידומת מאושרת בת 3 אותיות (למשל: btn, lbl, inp, lst, cmb, txt).
2. חובה לשים קו תחתון (_) מיד לאחר הקידומת (למשל: btn_submit).
3. אסור להצמיד מספרים לאותיות! חובה להפריד מספרים עם קו תחתון (btn_snippet_1 ולא btn_snippet1).
4. שמות אוטומטיים וגנריים של ה-Designer (כמו pushButton_1) מסוננים אוטומטית.

🤔 למה אנחנו עובדים ככה (הסיבה לחוקים)?
----------------------------------------
החוקים הללו נולדו מתוך המעבר מפריימוורק ה-Kivy ל-PySide6. עבודה עם שמות גנריים
יצרה סרבול וחוסר נוחות בקוד. המבנה הנוכחי מבטיח קוד קריא, מאורגן, מונע טעויות הקלדה,
ומאפשר למערכת האוטומטית למפות את הרכיבים בצורה מושלמת.

📂 מפת הקבצים ותפקידם בפרויקט (Project Architecture):
-----------------------------------------------------
* main.py         <- קובץ ההרצה הראשי. מדליק את ההגנות ומעלה את ה-GUI.
* core/boot.py    <- מנהל האתחול. בודק התאמת חתימות זמן של ה-UI מול הדיסק לפני הריצה.
* core/common/
  ├── integrity.py    <- "הקומפיילר החכם". סורק את ה-UI, אוכף חוקי שמות ויוצר את המיפוי.
  ├── mapping.py      <- קובץ נתונים סטטי ונקי. מכיל את חתימות הזמן, קבועי השמות ומפת ה-WIDGET_MAPS.
  ├── error_manager.py<- שומר הסף הגלובלי. חוטף קריסות, כותב לוגים ומקפיץ חלונות QMessageBox.
  └── app_host.py     <- "מארח האפליקציה". עמוד השדרה של הממשק, מנהל את החלון הראשי והניווט.

📢 בקשה מהמתכנת:
----------------
לכל אחד מהקבצים שנזכרו למעלה יש תיעוד (Docstring) מפורט, עמוק ומורחב בראש הקובץ,
המציג את סדר הפעולות המלא, את הכלים הזמינים בו ואת הרקע הארכיטקטוני שלו.
אנא בקר בשאר הקבצים וקרא את התיאור שלהם כדי להכיר את המערכת לעומק!
"""

from pathlib import Path
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from core.boot import run_startup_checks
from core.common.app_host import PySnipsHost
from core.common.error_manager import AppErrorHandler

if __name__ == "__main__":


    # 1. הרצת מנהל סדר הפעולות (חתימות הזמן מול ווינדוס)
    if not run_startup_checks():
        sys.exit(1)


    # 3. הפעלת ה-GUI של האפליקציה
    app = QApplication(sys.argv)
    # כפיית כיווניות שמאל-לימין כדי למנוע היפוך אוטומטי של ה-Layouts
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    window = PySnipsHost()
    window.show()

    ico = Path(__file__).resolve().parent / "icons" / "dnjd.ico"
    if not ico.exists():
        AppErrorHandler.handle_error(
            user_message="אופס! הפעולה נכשלה, לא הצלחנו לעבד את המידע הגרפי.",
            dev_message="התרחשה שגיאת ValueError מלאכותית לצורך בדיקת ערוצי המערכת.",
            severity="WARNING",
            solution_hint="אין צורך לתקן כלום, זו שגיאה יזומה כדי לראות שהלוג והחלון עובדים בתיאום.",
            show_terminal=True,  # רוצים לראות בטרמינל
            show_log=True,  # רוצים שיירשם בקובץ pysnips.log
            show_gui=True  # רוצים שיקפוץ חלון למשתמש
        )
    sys.exit(app.exec())