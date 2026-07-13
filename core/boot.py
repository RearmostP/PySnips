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
    *   `get_categories`: טוען את רשימת הקטגוריות מקובץ `categorys.json`.
    *   `update_categories_file`: מוסיף קטגוריה חדשה ל-`categorys.json`.
    *   `rebuild_category_index`: בונה מחדש את אינדקס הקטגוריות על ידי סריקת תיקיות השליפים.
    *   `ensure_category_files_exist`: כעת רק מוודאת שתיקיית `SNIPS_DATA_DIR` קיימת, ללא יצירת קבצי JSON נפרדים לקטגוריות.

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

from core.tools.common.app_paths import AppPaths
from core.tools.common.error_manager import AppDebugger, AppErrorHandler
from core.tools.search.snippet_search_engine import SnippetSearchEngine


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
        AppErrorHandler.handle_error(
            user_message=f"לא הצליח לטעון פונט מהנטיו {font_path}",
            severity="WARNING"
        )
        return ""

    font_families = QFontDatabase.applicationFontFamilies(font_id)
    if font_families:
        font_name = font_families[0]
        return font_name
    return ""


def get_categories() -> list:
    """החזר קטגוריות מ-CATEGORYS_JSON, בנה מחדש את האינדקס במידת הצורך."""
    try:
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
            dev_message=f"שגיאה בעדכון קובץ הקטגוריות categorys.json: {str(e)}",
            severity="ERROR"
        )


def rebuild_category_index() -> list:
    """סרוק את SNIPS_DATA_DIR לחיפוש קבצי JSON לכל קטגוריה וכתוב את CATEGORYS_JSON."""
    try:
        AppDebugger.log(f"בונה מחדש את אינדקס הקטגוריות מהדיסק: {AppPaths.SNIPS_DATA_DIR}")
        dir_path = Path(AppPaths.SNIPS_DATA_DIR)
        dir_path.mkdir(parents=True, exist_ok=True)

        categories = []
        for p in dir_path.glob('*/snips.json'): # Changed glob pattern to look for snips.json in subdirectories
            try:
                # Extract category name from parent directory
                cat_name = p.parent.name
                categories.append(cat_name)
            except Exception as e:
                AppDebugger.log(f"קריאת הקובץ נכשלה {p.name}: {str(e)}")
                pass

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
            dev_message=f"שגיאה בבניית אינדקס הקטגוריות categorys.json: {str(e)}",
            severity="ERROR"
        )
        return []


def ensure_category_files_exist(categories: list | None = None) -> None:
    """
    פונקציה זו נועדה במקור לוודא שקובץ JSON לכל קטגוריה קיים.
    בהתאם לבקשה, לוגיקת יצירת קבצי ה-JSON הנפרדים הוסרה.
    כעת, היא רק מוודאת שתיקיית SNIPS_DATA_DIR קיימת.
    """
    try:
        AppDebugger.log("בודק אם תיקיית נתוני השליפים קיימת...")
        dir_path = Path(AppPaths.SNIPS_DATA_DIR)
        dir_path.mkdir(parents=True, exist_ok=True)
        AppDebugger.log(f"תיקיית נתוני השליפים קיימת או נוצרה: {dir_path}")

    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאה בבדיקת/יצירת תיקיית נתוני השליפים",
            dev_message=str(e),
            severity="ERROR"
        )


def rebuild_search_index() -> bool:
    """Builds the Whoosh search index from the current snippets files on disk."""
    try:
        AppDebugger.log("Boot: rebuilding snippet search index from disk...")
        search_engine = SnippetSearchEngine()
        search_engine.rebuild_index_from_disk()
        AppDebugger.log("Boot: snippet search index rebuilt successfully.")
        return True
    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאה בעדכון אינדקס החיפוש",
            dev_message=f"Boot: failed rebuilding search index: {str(e)}",
            severity="WARNING",
            show_gui=False,
        )
        return False


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

        rebuild_search_index()

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

        AppDebugger.log("מנהל אתחול: בדיקות השלמות הסתיימו בהצלחה. המערכת מוכנה." + "\n")
        return True

    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="כשל פנימי קריטי במהלך הרצת מפת האתחול.",
            severity="CRITICAL"
        )
        return False
