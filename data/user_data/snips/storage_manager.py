import os
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime

# ייבוא הרכיבים הארכיטקטוניים והנתיבים הנייטיביים שלך
from core.common.app_paths import AppPaths
from core.common.error_manager import AppErrorHandler, AppDebugger


# =====================================================================
# פונקציות עזר רגילות ל-Data Class
# =====================================================================
def generate_unique_id() -> str:
    return str(uuid.uuid4())


def get_current_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =====================================================================
# 1. מודל הנתונים (Data Class) של השליף
# =====================================================================
@dataclass
class Snippet:
    title: str                                    # כותרת השליף
    md_file_name: str                             # שם קובץ ה-Markdown (למשל: 'basic_loop.md')
    category: str                                 # קטגוריה (Python, SQL, Git)
    tags: list[str] = field(default_factory=list) # תגיות לסינון מהיר (regex, loop)
    description: str = ""                         # תיאור קצר (לצורך תצוגה מהירה ברשימה)
    id: str = field(default_factory=generate_unique_id)
    created_at: str = field(default_factory=get_current_timestamp)

    def to_dict(self) -> dict:
        """המרת השליף למילון לצורך שמירה באינדקס ה-JSON"""
        return self.__dict__

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


# =====================================================================
# 2. מנהל האחסון (Storage Manager)
# =====================================================================
class StorageManager:
    #  שימוש בנתיבים המוחלטים והבטוחים מתוך AppPaths
    # הופכים את ה-Path לאובייקט קובץ סופי
    DB_PATH = AppPaths.SNIPS_DATA_DIR / "snippets.json"

    @classmethod
    def save_snippets(cls, snippets_list: list[Snippet]) -> bool:
        """מקבל רשימה של אובייקטי Snippet ושומר אותם כקובץ JSON אחד"""
        try:
            raw_data = [snip.to_dict() for snip in snippets_list]

            # כתיבה פיזית ישירה (התיקייה כבר מובטחת מקובץ ה-boot)
            with open(cls.DB_PATH, mode="w", encoding="utf-8") as f:
                json.dump(raw_data, f, indent=4, ensure_ascii=False)

            AppDebugger.log(f"💾 מנהל האחסון: {len(snippets_list)} שליפים נשמרו בהצלחה.")
            return True

        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="שגיאת מערכת: נכשלה שמירת השליפים לקובץ.",
                severity="ERROR"
            )
            return False

    @classmethod
    def load_snippets(cls) -> list[Snippet]:
        """טוען את קובץ ה-JSON ומחזיר רשימה של אובייקטי Snippet חיים"""
        # אם הקובץ לא קיים (למשל בהפעלה הראשונה אי פעם של התוכנה)
        if not os.path.exists(cls.DB_PATH):
            AppDebugger.log("🔍 מנהל האחסון: לא נמצא קובץ שמור, מחזיר רשימה ריקה.")
            return []

        try:
            with open(cls.DB_PATH, mode="r", encoding="utf-8") as f:
                raw_data = json.load(f)

            snippets_list = [Snippet.from_dict(item) for item in raw_data]
            AppDebugger.log(f"מנהל האחסון: נטענו {len(snippets_list)} שליפים מהדיסק.")
            return snippets_list

        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="שגיאת מערכת: קובץ השליפים פגום או שלא ניתן לקרוא אותו.",
                severity="ERROR"
            )
            return []