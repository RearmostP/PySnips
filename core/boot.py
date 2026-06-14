# core/boot.py
"""
🚀 PySnips 0.4 - Bootstrapper & Startup Sequence Manager
========================================================

📄 סדר הפעולות המלא בעת הפעלת האפליקציה (Startup Lifecycle):
-----------------------------------------------------------
1. [main.py]  <- המשתמש מריץ את הקובץ הראשי.
2. [main.py]  <- הדבר הראשון שמופעל הוא ה-setup_error_manager() כדי להבטיח הגנה גלובלית מקריסות.
3. [main.py]  <- קריאה לפונקציה run_startup_checks() שנמצאת כאן בקובץ ה-boot.
4. [boot.py]  <- המערכת מחשבת את הנתיב לתיקיית ui/ וסורקת את כל קובצי ה-.ui הקיימים פיזית בדיסק.
5. [boot.py]  <- המערכת שולפת מהדיסק את זמן השינוי האחרון (mtime) של כל קובץ ומעצבת אותו לפורמט קריא.
6. [boot.py]  <- המערכת מייבאת את המילון הסטטי UI_TIMESTAMPS מתוך קובץ ה-mapping.py.
7. [boot.py]  <- מתבצעת בדיקת תאימות ראשונה: האם רשימת הקבצים בדיסק זהה לחלוטין לרשימת הקבצים במיפוי?
8. [boot.py]  <- מתבצעת בדיקת תאימות שנייה: האם חתימת הזמן של כל קובץ תואמת על השנייה לחתימה שבקוד?
9. [main.py]  <- במידה ויש חוסר סנכרון, ה-boot מחזיר False, מדפיס שגיאה ברורה, והאפליקציה נחסמת ויוצאת (sys.exit).
10.[main.py]  <- במידה והכל מסונכרן ב-100%, ה-boot מחזיר True, ורק אז ה-QApplication ו-PySnipsHost עולים בבטחה.
"""
import os
from pathlib import Path
from datetime import datetime

from core.common.app_paths import AppPaths


def run_startup_checks() -> bool:
    """
    מנהל סדר פעולות חכם הבודק התאמת תאריכי שינוי (mtime) של קובצי ה-UI
    מול מילון ה-UI_TIMESTAMPS שנשמר בתוך mapping.py.
    """
    print("🚀 מנהל סדר פעולות: בודק סנכרון קובצי ממשק...")



    if not AppPaths.UI_DIR.exists():
        print(f"❌ [שגיאת אתחול] תיקיית ה-UI לא נמצאה בנתיב: {AppPaths.UI_DIR}")
        return False

    # 1. שליפת קובצי ה-ui הקיימים בדיסק
    ui_files = list(AppPaths.UI_DIR.glob("*.ui"))
    if not ui_files:
        print("❌ [שגיאת אתחול] לא נמצאו קובצי .ui בתוך תיקיית ui/")
        return False

    # 2. בניית מילון חתימות הזמן הנוכחיות מהדיסק (בדיוק באותו פורמט של ה-mapping שלך)
    live_timestamps = {
        f.name: datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M:%S')
        for f in ui_files
    }

    # 3. ייבוא מילון חתימות הזמן השמורות מתוך קובץ המיפוי המעודכן
    try:
        # בגלל ששניהם באותה תיקייה (core/common), הייבוא הוא ישיר
        from core.common.mapping import UI_TIMESTAMPS
    except ImportError as e:
        print("\n" + "!" * 65)
        print("❌ [שגיאת אתחול] לא ניתן לייבא את UI_TIMESTAMPS מתוך mapping.py!")
        print(f"   <- שגיאה: {e}")
        print("   <- פתרון: הרץ את core/common/mapping.py כדי לייצר את הקובץ מחדש.")
        print("!" * 65 + "\n")
        return False

    # 4. הבדיקה המרכזית: השוואה בין המילונים
    # נבדוק קודם כל אם יש קובץ חדש בדיסק שלא רשום במפה, או קובץ שנמחק
    if set(live_timestamps.keys()) != set(UI_TIMESTAMPS.keys()):
        print("\n" + "!" * 65)
        print("❌ [שגיאת חוסר סנכרון] כמות או שמות קובצי ה-UI בדיסק אינם תואמים למיפוי!")
        print(f"   <- קבצים בדיסק: {list(live_timestamps.keys())}")
        print(f"   <- קבצים במיפוי: {list(UI_TIMESTAMPS.keys())}")
        print("\n   <- פתרון: הרץ את core/common/mapping.py כדי לעדכן את המפות.")
        print("!" * 65 + "\n")
        return False

    # כעת נבדוק קובץ-קובץ האם התאריך שונה
    for file_name, live_time in live_timestamps.items():
        mapped_time = UI_TIMESTAMPS.get(file_name)

        if live_time != mapped_time:
            print("\n" + "!" * 65)
            print(f"❌ [שגיאת חוסר סנכרון] קובץ ה-UI '{file_name}' עודכן בדיזיינר אך לא סונכרן בקוד!")
            print(f"   <- זמן עדכון בדיזיינר: {live_time}")
            print(f"   <- זמן סנכרון בקוד:     {mapped_time}")
            print("\n   <- הסיבה: שמרת שינויים במעצב, אך לא הרצת את המיפוי מחדש.")
            print("   <- פתרון: הרץ את core/common/mapping.py כדי לרענן את חתימות הזמן והרכיבים.")
            print("!" * 65 + "\n")
            return False

    print("✅ מנהל סדר פעולות: חתימות הזמן מסונכרנות ב-100%. האפליקציה בטוחה להפעלה.")
    print("-" * 65)
    return True