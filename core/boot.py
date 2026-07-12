"""
מטרת הקובץ: מנהל אתחול ובדיקות שלמות של המערכת (Bootstrapper & Integrity Checks)
---------------------------------------------------------------------------------
קובץ זה אחראי על הכנת סביבת הריצה של האפליקציה לפני שהיא מתחילה לפעול.
הוא מבצע סדרה של בדיקות חיוניות וטעינת משאבים ראשוניים כדי להבטיח שהמערכת יציבה ומוכנה לשימוש.

מה הוא בודק ומנהל?
------------------
1.  **בדיקת שלמות נתיבים ותיקיות (AppPaths.INTEGRITY_MAP)**:
    *   סורק את כל הנתיבים והתיקיות המוגדרים במפת השלמות (INTEGRITY_MAP) ב-`AppPaths`.
    *   מוודא שכל התיקיות והקבצים החיוניים קיימים.
    *   יוצר תיקיות חסרות במידת הצורך.
    *   יוצר קובצי ברירת מחדל (כמו `categorys.json`) אם הם חסרים.
    *   מטפל בשגיאות קריטיות שעלולות למנוע את המשך פעולת האפליקציה.

2.  **ניהול קטגוריות (get_categories, update_categories_file, rebuild_category_index)**:
    *   טוען את רשימת הקטגוריות מקובץ `categorys.json`.
    *   במקרה של כשל בטעינה או קובץ חסר, בונה מחדש את אינדקס הקטגוריות על ידי סריקת תיקיות השליפים.
    *   מוודא שקיימים קבצי JSON ריקים עבור כל קטגוריה בתיקיית הנתונים.

3.  **טעינת גופנים מותאמים אישית (load_custom_font)**:
    *   סורק את תיקיית הגופנים (FONTS_DIR) וטוען אוטומטית קובצי גופן (.ttf, .otf) למערכת.
    *   מאפשר שימוש בגופנים מותאמים אישית ברחבי האפליקציה.

4.  **טיפול בשגיאות (AppErrorHandler)**:
    *   משתמש במנגנון הטיפול בשגיאות הגלובלי כדי לדווח על כשלים קריטיים או אזהרות במהלך האתחול.

בסיום תהליך זה, האפליקציה מוכנה להעלות את ממשק המשתמש ולהתחיל את לולאת האירועים הראשית.
"""

import json
from pathlib import Path
from PySide6.QtGui import QFontDatabase

from core.common.app_paths import AppPaths
from core.common.error_manager import AppDebugger, AppErrorHandler


def _sanitize(name: str) -> str:
    """הפוך שם קטגוריה לשם קובץ בטוח לשימוש במערכת קבצים."""
    safe = ''.join(c for c in (name or '') if c.isalnum() or c in (' ', '_', '-')).strip()
    if not safe:
        return 'uncategorized'
    return safe.replace(' ', '_')


def _desanitize(filename: str) -> str:
    """הפוך את הסניטיזציה לתצוגה (הסר סיומת והחלף _ בכניסה)."""
    return Path(filename).stem.replace('_', ' ')


def load_custom_font(font_path: Path | str) -> str:
    """טוענת קובץ פונט לזיכרון ומחזירה את השם הרשמי שלו במערכת."""
    path_str = str(font_path)
    font_id = QFontDatabase.addApplicationFont(path_str)
    if font_id == -1:
        AppDebugger.log(f"טעינת הגופן נכשלה מהנתיב: {path_str}")
        return ""

    font_families = QFontDatabase.applicationFontFamilies(font_id)
    if font_families:
        font_name = font_families[0]
        AppDebugger.log(f"גופן המערכת נטען בהצלחה: {font_name}")
        return font_name
    return ""


def get_categories() -> list:
    """החזר קטגוריות מ-CATEGORYS_JSON, בנה מחדש את האינדקס במידת הצורך."""
    try:
        AppDebugger.log(f"טוען קטגוריות מהנתיב: {AppPaths.CATEGORYS_JSON}")
        with open(AppPaths.CATEGORYS_JSON, 'r', encoding='utf-8') as f:
            categories = json.load(f)
            AppDebugger.log(f"נמצאו ונטענו {len(categories)} קטגוריות לזיכרון")
            return categories
    except Exception as e:
        AppDebugger.log(f"טעינת הקטגוריות נכשלה, בונה מחדש את האינדקס: {str(e)}")
        return rebuild_category_index()


def update_categories_file(new_category: str):
    """
    מוסיף קטגוריה חדשה לקובץ categorys.json אם אינה קיימת.
    """
    try:
        categories = get_categories() # קבל את רשימת הקטגוריות הנוכחית
        if new_category not in categories:
            categories.append(new_category)
            AppDebugger.log(f"מוסיף קטגוריה חדשה לקובץ: {new_category}")
            with open(AppPaths.CATEGORYS_JSON, 'w', encoding='utf-8') as f:
                json.dump(categories, f, ensure_ascii=False, indent=2)
            AppDebugger.log(f"קובץ categorys.json עודכן בהצלחה עם הקטגוריה: {new_category}")
        else:
            AppDebugger.log(f"הקטגוריה '{new_category}' כבר קיימת בקובץ categorys.json")
    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאה בעדכון קובץ הקטגוריות",
            dev_message=f"Error updating categorys.json: {str(e)}",
            severity="ERROR"
        )


def rebuild_category_index() -> list:
    """סרוק את SNIPS_DATA_DIR לחיפוש קבצי JSON לכל קטגוריה וכתוב את CATEGORYS_JSON."""
    try:
        AppDebugger.log(f"בונה מחדש את אינדקס הקטגוריות מהדיסק: {AppPaths.SNIPS_DATA_DIR}")
        dir_path = Path(AppPaths.SNIPS_DATA_DIR)
        dir_path.mkdir(parents=True, exist_ok=True)

        categories = []
        for p in dir_path.glob('*.json'):
            if p.name == Path(AppPaths.CATEGORYS_JSON).name:
                continue
            try:
                AppDebugger.log(f"קורא קובץ קטגוריה: {p.name}")
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    cat = data[0].get('category')
                    if cat:
                        categories.append(cat)
                        continue
            except Exception as e:
                AppDebugger.log(f"קריאת הקובץ נכשלה {p.name}: {str(e)}")
                pass
            categories.append(_desanitize(p.name))

        seen = set()
        out = []
        for c in categories:
            if c not in seen:
                seen.add(c)
                out.append(c)

        AppDebugger.log(f"שומר {len(out)} קטגוריות לקובץ האינדקס: {AppPaths.CATEGORYS_JSON}")
        with open(AppPaths.CATEGORYS_JSON, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

        AppDebugger.log(f"מנהל אתחול: אינדקס הקטגוריות נבנה מחדש בהצלחה עם {len(out)} רשומות")
        return out

    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאה בבניית אינדקס הקטגוריות",
            dev_message=str(e),
            severity="ERROR"
        )
        return []


def ensure_category_files_exist(categories: list | None = None) -> None:
    """ודא שקובץ JSON לכל קטגוריה קיים"""
    try:
        AppDebugger.log("בודק אם קבצי הקטגוריות קיימים בדיסק...")
        if categories is None:
            categories = get_categories()
        dir_path = Path(AppPaths.SNIPS_DATA_DIR)
        dir_path.mkdir(parents=True, exist_ok=True)

        created = 0
        for cat in categories:
            safe = _sanitize(cat)
            file_path = dir_path / f"{safe}.json"
            if not file_path.exists():
                try:
                    AppDebugger.log(f"יוצר קובץ קטגוריה חסר: {file_path}")
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
                    created += 1
                except Exception as e:
                    AppDebugger.log(f"יצירת הקובץ נכשלה {file_path}: {str(e)}")
                    pass
            else:
                AppDebugger.log(f"קובץ הקטגוריה כבר קיים: {file_path}")

        if created:
            AppDebugger.log(f"מנהל אתחול: נוצרו {created} קבצים חסרים עבור הקטגוריות")
        else:
            AppDebugger.log(f"כל {len(categories)} קבצי הקטגוריות כבר קיימים")
    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאה בבדיקת קבצי הקטגוריות",
            dev_message=str(e),
            severity="ERROR"
        )


def run_startup_checks() -> bool:
    """
    מנהל האתחול - סורק את מפת המערכת, אוכף נתיבים וטוען משאבי מערכת (פונטים).
    """
    try:
        AppDebugger.log("מנהל אתחול: מתחיל בדיקת שלמות מתוך מפת הנתיבים...")

        # עוברים איטרטיבית על המילון: נתיב והסטטוס שלו (True=חובה, False=אופציונלי)
        for path_obj, is_critical in AppPaths.INTEGRITY_MAP.items():
            path = Path(path_obj)
            is_file = path.suffix != ""

            if not path.exists():
                if is_file:
                    try:
                        if path == Path(AppPaths.CATEGORYS_JSON):
                            path.parent.mkdir(parents=True, exist_ok=True)
                            default_cats = ["python", "pyside6"]
                            AppDebugger.log(f"יוצר קובץ קטגוריות ברירת מחדל: {path}")
                            with open(path, 'w', encoding='utf-8') as f:
                                json.dump(default_cats, f, ensure_ascii=False, indent=2)
                            AppDebugger.log(
                                f"מנהל אתחול: נוצר קובץ קטגוריות ברירת מחדל עם {len(default_cats)} רשומות: {path}")
                            continue
                    except Exception as e:
                        AppErrorHandler.handle_error(
                            error_obj=e,
                            user_message="שגיאת אתחול: לא ניתן ליצור קובץ ברירת-מחדל.",
                            dev_message=str(e),
                            severity="CRITICAL"
                        )
                        return False

                    if is_critical:
                        AppErrorHandler.handle_error(
                            user_message="שגיאת אתחול: קובץ מערכת חיוני חסר.",
                            dev_message=f"קובץ קריטי חסר בדיסק: {path}",
                            severity="CRITICAL"
                        )
                        return False
                else:
                    status_text = "חובה" if is_critical else "אופציונלי"
                    AppDebugger.log(f"יוצר תיקייה חסרה ({status_text}): {path}")
                    path.mkdir(parents=True, exist_ok=True)
                    AppDebugger.log(f"מנהל אתחול: התיקייה נוצרה בהצלחה ({status_text}): {path}")

        try:
            ensure_category_files_exist()
        except Exception:
            pass

        # סריקה וטעינה אוטומטית של פונטים מותאמים אישית
        try:
            if hasattr(AppPaths, "FONTS_DIR"):
                fonts_dir = AppPaths.FONTS_DIR
            else:
                fonts_dir = Path("core/assets/fonts")

            AppDebugger.log(f"מנהל אתחול: בודק את תיקיית הגופנים בנתיב {fonts_dir.resolve()}")

            if fonts_dir.exists():
                AppDebugger.log("מנהל אתחול: סורק גופנים מותאמים אישית...")
                for font_file in fonts_dir.glob("*.*"):
                    if font_file.suffix.lower() in [".ttf", ".otf"]:
                        load_custom_font(font_file)
            else:
                AppDebugger.log(f"מנהל אתחול: תיקיית הגופנים לא נמצאה בנתיב {fonts_dir}")

        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="שגיאה בטעינת פונטים של המערכת",
                dev_message=f"מנהל אתחול: שגיאה במהלך סריקת תיקיית הגופנים: {str(e)}",
                severity="WARNING"
            )

        AppDebugger.log("מנהל אתחול: בדיקות השלמות הסתיימו בהצלחה. המערכת מוכנה.")
        return True

    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="כשל פנימי קריטי במהלך הרצת מפת האתחול.",
            severity="CRITICAL"
        )
        return False