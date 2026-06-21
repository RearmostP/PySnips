"""
🚀 PySnips 0.4 - Bootstrapper & Startup Sequence Manager
========================================================

 סדר הפעולות המלא בעת הפעלת האפליקציה (Startup Lifecycle):
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
from datetime import datetime

from core.common.app_paths import AppPaths
from core.common.error_manager import AppErrorHandler, AppDebugger


def run_startup_checks() -> bool:
    """
    מנהל סדר פעולות חכם הבודק התאמת תאריכי שינוי (mtime) של קובצי ה-UI
    מול מילון ה-UI_TIMESTAMPS שנשמר בתוך mapping.py.
    """
    AppDebugger.log(" מנהל סדר פעולות: בודק סנכרון קובצי ממשק...")

    # בדיקת קיום תיקיית ה-UI
    if not AppPaths.UI_DIR.exists():
        AppErrorHandler.handle_error(
            user_message="שגיאת אתחול: תיקיית ממשק המשתמש חסרה.",
            dev_message=f"תיקיית ה-UI לא נמצאה בנתיב המצופה: {AppPaths.UI_DIR}",
            severity="CRITICAL",
            solution_hint="וודא שתיקיית ה-ui קיימת בנתיב המוגדר ב-AppPaths."
        )
        return False

    # 1. שליפת קובצי ה-ui הקיימים בדיסק
    ui_files = list(AppPaths.UI_DIR.glob("*.ui"))
    if not ui_files:
        AppErrorHandler.handle_error(
            user_message="שגיאת אתחול: לא נמצאו קובצי ממשק.",
            dev_message=f"תיקיית ה-UI קיימת אך ריקה מקובצי .ui בנתיב: {AppPaths.UI_DIR}",
            severity="CRITICAL",
            solution_hint="וודא שקובצי ה-Designer נשמרו בתוך תיקיית ui/ עם סיומת .ui תקינה."
        )
        return False

    # 2. בניית מילון חתימות הזמן הנוכחיות מהדיסק
    live_timestamps = {
        f.name: datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M:%S')
        for f in ui_files
    }

    # 3. ייבוא מילון חתימות הזמן השמורות מתוך קובץ המיפוי
    try:
        from core.common.mapping import UI_TIMESTAMPS
    except ImportError as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאת אתחול: מפת רכיבי המערכת חסרה או פגומה.",
            dev_message="לא ניתן לייבא את המילון הסטטי UI_TIMESTAMPS מתוך קובץ ה-mapping.py.",
            severity="CRITICAL",
            solution_hint="הרצי את הסקריפט core/common/mapping.py כדי לייצר ולרענן את קובץ המיפוי מחדש."
        )
        return False

    # 4. הבדיקה המרכזית: השוואה בין המילונים (שמות וכמות קבצים)
    if set(live_timestamps.keys()) != set(UI_TIMESTAMPS.keys()):
        AppErrorHandler.handle_error(
            user_message="שגיאת סנכרון: מבנה קובצי הממשק בדיסק שונה מהקוד.",
            dev_message=(
                f"כמות או שמות קובצי ה-UI בדיסק אינם תואמים למיפוי!\n"
                f"<- קבצים בדיסק: {list(live_timestamps.keys())}\n"
                f"<- קבצים במיפוי: {list(UI_TIMESTAMPS.keys())}"
            ),
            severity="CRITICAL",
            solution_hint="התווסף או נמחק קובץ UI. הרץ את core/common/mapping.py כדי לעדכן את המפות ולסנכרן את הפרויקט."
        )
        return False

    # כעת נבדוק קובץ-קובץ האם התאריך שונה (חתימות זמן)
    for file_name, live_time in live_timestamps.items():
        mapped_time = UI_TIMESTAMPS.get(file_name)

        if live_time != mapped_time:
            AppErrorHandler.handle_error(
                user_message=f"שגיאת סנכרון: קובץ הממשק '{file_name}' עודכן אך לא סונכרן.",
                dev_message=(
                    f"קובץ ה-UI '{file_name}' עודכן בדיזיינר אך חתימת הזמן בקוד ישנה!\n"
                    f"<- זמן עדכון בדיזיינר: {live_time}\n"
                    f"<- זמן סנכרון בקוד:     {mapped_time}"
                ),
                severity="CRITICAL",
                solution_hint=(
                    f"שמרת שינויים ב-Qt Designer עבור '{file_name}', אך לא עדכנת את המיפוי.\n"
                    f"הרץ את core/common/mapping.py כדי לרענן חתימות זמן ורכיבים דינמיים."
                )
            )
            return False

    AppDebugger.log(" מנהל סדר פעולות: חתימות הזמן מסונכרנות ב-100%. האפליקציה בטוחה להפעלה.")
    return True