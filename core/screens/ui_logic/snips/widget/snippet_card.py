"""
מטרת הקובץ: לוגיקת עזר לכרטיסיית שליף (Snippet Card Helper Logic)
-----------------------------------------------------------------
קובץ זה מכיל פונקציות עזר סטטיות המשמשות לטיפול בנתונים הקשורים לכרטיסיות שליפים.
הוא מופרד ממחלקת ה-UI של כרטיסיית השליף (`SnippetCardWidget`) כדי לשמור על
הפרדה ברורה בין תצוגה ללוגיקה.

תפקידים עיקריים:
1.  **הגדרת קבועים**:
    *   `DEFAULT_TITLE`: כותרת ברירת מחדל לשליף ללא כותרת.
    *   `CONTENT_READ_ERROR`: הודעת שגיאה כללית לקריאת תוכן.
    *   `CONTENT_FILE_MISSING`: הודעת שגיאה כאשר קובץ התוכן חסר.

2.  **מבנה נתונים (SnippetContent)**:
    *   `@dataclass` פשוט לאחסון תוכן השליף ודגל המציין אם הוא Markdown.

3.  **אחזור כותרת (get_snippet_title)**:
    *   מקבל מטא-נתונים של שליף ומחזיר את הכותרת שלו, עם טיפול במקרה שהכותרת חסרה.

4.  **קריאת תוכן שליף (read_snippet_content)**:
    *   מקבל מטא-נתונים של שליף.
    *   קורא את תוכן השליף מקובץ פיזי המצוין ב-`content_file`.
    *   מטפל במקרים של קובץ חסר או שגיאות קריאה, ומחזיר אובייקט `SnippetContent` מתאים.

קובץ זה מספק את הלוגיקה הבסיסית הנדרשת לכרטיסיית שליף כדי להציג את נתוניה,
מבלי לערב את מחלקת ה-UI בפרטי אחזור הנתונים מהדיסק.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


DEFAULT_TITLE = "ללא כותרת"
CONTENT_READ_ERROR = "שגיאה בקריאת תוכן השליף."
CONTENT_FILE_MISSING = "קובץ התוכן לא נמצא."


@dataclass(frozen=True)
class SnippetContent:
    text: str
    is_markdown: bool


def get_snippet_title(snippet_meta: Mapping[str, object]) -> str:
    title = snippet_meta.get("title", DEFAULT_TITLE)
    return str(title) if title else DEFAULT_TITLE


def read_snippet_content(snippet_meta: Mapping[str, object]) -> SnippetContent:
    content_file = snippet_meta.get("content_file", "")
    content_file_path = Path(str(content_file))

    if not content_file_path.exists():
        return SnippetContent(CONTENT_FILE_MISSING, is_markdown=False)

    try:
        return SnippetContent(
            content_file_path.read_text(encoding="utf-8"),
            is_markdown=True,
        )
    except OSError:
        return SnippetContent(CONTENT_READ_ERROR, is_markdown=False)