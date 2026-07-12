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
  ├── error_manager.py<- שומר הסף הגלובלי. חוטף קריסות, כותב לוגים ומקפיץ חלונות QMessageBox.
  └── dynamic_ui_loader.py     <- טוען קבצי ui דינאמחת בזמן ריצה

* core/system_tools
    └── mapping.py      <- קובץ נתונים סטטי ונקי. מכיל את חתימות הזמן, קבועי השמות ומפת ה-WIDGET_MAPS.


📢 בקשה מהמתכנת:
----------------
לכל אחד מהקבצים שנזכרו למעלה יש תיעוד (Docstring) מפורט, עמוק ומורחב בראש הקובץ,
המציג את סדר הפעולות המלא, את הכלים הזמינים בו ואת הרקע הארכיטקטוני שלו.
אנא בקר בשאר הקבצים וקרא את התיאור שלהם כדי להכיר את המערכת לעומק!
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon


from core.common.screen_manager import ScreenManager # Corrected import
from core.boot import run_startup_checks
from core.common.error_manager import AppDebugger

from core.screens.ui_logic.home.home_screen import HomeScreen
from core.screens.ui_logic.snips.snippets_screen import SnippetsScreen



def main():
    # 1. יצירת מופע האפליקציה של Qt
    app = QApplication(sys.argv)

    # 2. הרצת בדיקות השלמות תחילה
    if not run_startup_checks():
        AppDebugger.log("בדיקות השלמות נכשלו. הריצה הסתיימה.")
        sys.exit(1)

    AppDebugger.log("בדיקות השלמות עברו בהצלחה. מתחיל אתחול...")

    # 3. יצירת מנהל המסכים
    screen_manager = ScreenManager()
    screen_manager.resize(1024, 768)  # הגדרת גודל החלון הראשי
    screen_manager.setWindowTitle("PySnips")
    screen_manager.setWindowIcon(QIcon("assets/icons/pysnips.ico"))

    # 4. טעינת מסך הבית
    home_screen = HomeScreen(screen_manager)
    home_screen.setup_logic()
    home_screen.load_home_screen()

    # 5. טעינת מסך השליפים
    snippets_screen = SnippetsScreen(parent=screen_manager)
    snippets_screen.setup_events()
    screen_manager.register_screen("snippets", snippets_screen)



    # 6. הצגת מנהל המסכים (החלון הראשי של האפליקציה)
    screen_manager.show()

    # 7. לולאת האירועים המרכזית של Qt
    sys.exit(app.exec())


if __name__ == "__main__":
    main()