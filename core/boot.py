import os
from pathlib import Path
from core.common.app_paths import AppPaths
from core.common.error_manager import AppDebugger, AppErrorHandler

def run_startup_checks() -> bool:
    """
    מנהל האתחול - סורק את מפת המערכת ואוכף קיום נתיבים לפי רמת קריטיות.
    """
    try:
        AppDebugger.log(" Bootstrapper: מתחיל בדיקת שלמות מתוך מפת הנתיבים...")

        # עוברים איטרטיבית על המילון: נתיב והסטטוס שלו (True=חובה, False=אופציונלי)
        for path_obj, is_critical in AppPaths.INTEGRITY_MAP.items():
            # המרה ל-Path ליתר ביטחון (אם הוכנס סטרינג)
            path = Path(path_obj)

            # בודקים אם זה קובץ סופי (סיומת עם נקודה כמו .py) או תיקייה
            is_file = path.suffix != ""

            if not path.exists():
                if is_file:
                    # אם זה קובץ חסר והוא קריטי -> חוסמים ריצה
                    if is_critical:
                        AppErrorHandler.handle_error(
                            user_message="שגיאת אתחול: קובץ מערכת חיוני חסר.",
                            dev_message=f"קובץ חובה חסר בדיסק: {path}",
                            severity="CRITICAL"
                        )
                        return False
                else:
                    # זו תיקייה חסרה - מייצרים אותה בכל מקרה (גם אם היא אופציונלית וגם אם חובה)
                    path.mkdir(parents=True, exist_ok=True)
                    status_text = "חובה" if is_critical else "אופציונלית"
                    AppDebugger.log(f" Bootstrapper: יצר תיקיית {status_text} חסרה: {path}")

        AppDebugger.log(" Bootstrapper: בדיקת המפה הסתיימה בהצלחה. המערכת מוכנה.")
        return True

    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="כשל פנימי קריטי במהלך הרצת מפת האתחול.",
            severity="CRITICAL"
        )
        return False