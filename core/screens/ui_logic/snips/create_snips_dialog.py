"""
מטרת הקובץ: לוגיקה לדיאלוג יצירת שליף חדש (Create Snippet Dialog Logic)
-----------------------------------------------------------------------
קובץ זה מכיל את הלוגיקה העסקית והאינטראקציה עם ממשק המשתמש עבור הדיאלוג
המאפשר למשתמש ליצור ולשמור שליפים (snippets) חדשים.

תפקידים עיקריים:
1.  **ניהול שליפים (SnippetManager)**:
    *   אחראי על יצירה, עיבוד ושמירה של נתוני שליפים חדשים (כותרת, קטגוריה, תגיות, תוכן).
    *   מטפל ביצירת מזהים ייחודיים (UUID) ושמות קבצים בטוחים.
    *   שומר את תוכן השליף לקובץ Markdown נפרד.
    *   מעדכן את קובץ האינדקס `snips.json` עבור הקטגוריה הרלוונטית.

2.  **אינטראקציה עם UI (CreateSnipsDialog)**:
    *   טוען את קובץ ה-UI (`create_snips_dialog.ui`) באופן דינמי באמצעות `create_dynamic_ui_loader`.
    *   מחבר את כפתורי ה-UI (כמו "שמור" ו"בטל") לפונקציות הלוגיות המתאימות.
    *   טוען ומציג את רשימת הקטגוריות הקיימות ב-combobox.
    *   מטפל בלוגיקת גרירת הדיאלוג (mousePressEvent, mouseMoveEvent, mouseReleaseEvent).
    *   מציג הודעות למשתמש (אזהרות, הצלחה) באמצעות `QMessageBox`.

3.  **טיפול בשגיאות**:
    *   משתמש ב-`AppErrorHandler` לדיווח על שגיאות שונות במהלך תהליך יצירת ושמירת השליף.

קובץ זה מאפשר למשתמש להזין את כל הפרטים הנדרשים לשליף חדש, לשמור אותו למערכת הקבצים
ולעדכן את אינדקס הקטגוריות בצורה בטוחה ויעילה.
"""

from PySide6.QtCore import Qt

import json
import uuid
import re
from pathlib import Path

from core.common.app_paths import AppPaths
from core.common.dynamic_ui_loader import create_dynamic_ui_loader
from core.common.error_manager import AppDebugger, AppErrorHandler


def _sanitize(name: str) -> str:
    """הפוך שם קטגוריה לשם קובץ בטוח לשימוש במערכת קבצים."""
    safe = ''.join(c for c in (name or '') if c.isalnum() or c in (' ', '_', '-')).strip()
    if not safe:
        return 'uncategorized'
    return safe.replace(' ', '_')


class SnippetManager:
    """מנהל היצירה והשמירה של snippets - טיפול בלוגיקת העבודה הקשורה ל-snippets."""

    def __init__(self):
        self.tags_list = []

    def create_and_save(self, title: str, category: str, tags_str: str, content: str) -> bool:
        """
        יצירה ושמירה של snippet חדש.

        Args:
            title: כותרת ה-snippet
            category: קטגוריה
            tags_str: תגיות מופרדות בפסיקים
            content: תוכן ה-snippet

        Returns:
            bool: האם השמירה הצליחה
        """
        try:
            if not title or not content:
                AppErrorHandler.handle_error(
                    user_message="שם ותוכן הם שדות חובה",
                    severity="INFO",
                    show_terminal=False,
                    show_log=False,
                    show_gui=True
                )
                return False

            AppDebugger.log(f"📝 יוצר snippet חדש: '{title}' בקטגוריה '{category}'")

            # עיבוד התגיות
            self.tags_list = self._parse_tags(tags_str)

            # יצירת מזהה ייחודי
            snippet_id = str(uuid.uuid4())
            AppDebugger.log(f"  🆔 יצר ID snippet: {snippet_id}")

            # בנייה של שם קובץ קריא
            fname = self._make_content_filename(title, snippet_id)
            AppDebugger.log(f"  📄 יצר שם קובץ: {fname}")

            # קביעת תיקיית הקבצים לקטגוריה
            safe_cat = _sanitize(category)
            file_dir = AppPaths.SNIPS_FILES / safe_cat
            file_path = file_dir / fname

            snippet_data = {
                'id': snippet_id,
                'title': title,
                'category': category,
                'tags': self.tags_list,
                'content_file': str(file_path),
            }

            # שמירת קובץ התוכן
            if not self._save_content_file(snippet_id, content, title, category):
                return False

            # עדכון ה-snips.json של הקטגוריה
            self._save_snippets_json(snippet_data, category)

            AppDebugger.log(f"✅ SnippetManager: שמר snippet חדש בהצלחה: {title}")
            return True

        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="שגיאה בשמירת ה-snippet",
                dev_message=str(e),
                severity="ERROR"
            )
            return False

    @staticmethod
    def _parse_tags(tags_str: str) -> list:
        """עיבוד מחרוזת תגיות - הסרת כפילויות תוך שמירה על סדר."""
        seen = set()
        tags_list = []
        for tag in (tags_str or '').split(','):
            t = tag.strip()
            if not t or t in seen:
                continue
            seen.add(t)
            tags_list.append(t)
        return tags_list

    @staticmethod
    def _make_content_filename(title: str, snippet_id: str, maxlen: int = 50) -> str:
        """בנייה של שם קובץ בטוח, קריא - דוגמה: my-snippet-title-7f3a2b1c.md"""
        slug = re.sub(r"[^\w\s-]", "", (title or '').strip(), flags=re.UNICODE)
        slug = re.sub(r"[\s]+", "-", slug).strip("-")[:maxlen].lower()
        if not slug:
            slug = 'snippet'
        short_id = snippet_id.replace('-', '')[:8]
        return f"{slug}-{short_id}.md"

    @staticmethod
    def _save_content_file(snippet_id: str, content: str, title: str | None = None,
                           category: str | None = None) -> bool:
        """שמירת תוכן ה-snippet לקובץ markdown בתיקיית הקטגוריה."""
        try:
            safe_cat = _sanitize(category)
            dir_path = AppPaths.SNIPS_FILES / safe_cat
            dir_path.mkdir(parents=True, exist_ok=True)

            if title:
                fname = SnippetManager._make_content_filename(title, snippet_id)
            else:
                fname = f"{snippet_id}.md"

            file_path = dir_path / fname
            AppDebugger.log(f"💾 שומר תוכן snippet לדיסק: {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            AppDebugger.log(f"✅ תוכן snippet שומר בהצלחה: {file_path}")
            return True
        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="שגיאה בשמירת תוכן ה-snippet",
                dev_message=str(e),
                severity="ERROR"
            )
            return False

    @staticmethod
    def _save_snippets_json(snippet_data: dict, category: str | None = None) -> bool:
        """הוספה או יצירה של snips.json לכל קטגוריה."""
        try:
            safe_cat = _sanitize(category or snippet_data.get('category'))
            dir_path = AppPaths.SNIPS_FILES / safe_cat
            dir_path.mkdir(parents=True, exist_ok=True)

            snippets_file = dir_path / "snips.json"
            snippets = []

            if snippets_file.exists():
                AppDebugger.log(f"🔄 טוען אינדקס snippets מהזיכרון: {snippets_file}")
                with open(snippets_file, 'r', encoding='utf-8') as f:
                    try:
                        snippets = json.load(f)
                        AppDebugger.log(f"✅ טען {len(snippets)} snippets קיימים")
                    except Exception as e:
                        AppDebugger.log(f"⚠️ נכשל בפענוח snippets.json: {str(e)}, מתחיל מחדש")
                        snippets = []
            else:
                AppDebugger.log(f"📄 יוצר קובץ אינדקס snippets חדש: {snippets_file}")

            snippets.append(snippet_data)

            AppDebugger.log(f"💾 שומר {len(snippets)} snippets לדיסק: {snippets_file}")
            with open(snippets_file, 'w', encoding='utf-8') as f:
                json.dump(snippets, f, ensure_ascii=False, indent=2)
            AppDebugger.log(f"✅ אינדקס snippets שומר בהצלחה")

            return True
        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message=f"שגיאה בעדכון snips.json של הקטגוריה '{category}'",
                dev_message=str(e),
                severity="ERROR"
            )
            return False


class CreateSnipsDialog(create_dynamic_ui_loader(AppPaths.CREATE_SNIPS_DIALOG)):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.snippet_manager = SnippetManager()
        self.drag_pos = None

    def setup_events(self):
        """
        פונקציה שמחברת את האירועים והכפתורים.
        נקראת רק לאחר שקובץ ה-UI נטען במלואו לזיכרון.
        """
        AppDebugger.log("CreateSnipsDialog: מחבר אירועים ורכיבי ממשק וחיבור כפתורים לפונקציות...")

        self.btn_save.clicked.connect(self.save_snippet)
        self.btn_cancel.clicked.connect(self.close)

        # טען קטגוריות וצרף כפתורים דינמיים + עדכן את ה-combo
        self._load_category_buttons()

    def save_snippet(self):
        """
        שמירת שליף חדש לתיקייה
        קורא ל-SnippetManager לביצוע הלוגיקה
        """
        try:
            title = self.inp_title_input.text()
            category = self.cmb_category_spinner.currentText()
            tags = self.inp_tags_input.text()
            content = self.txt_content_input.toPlainText()

            if self.snippet_manager.create_and_save(title, category, tags, content):
                AppDebugger.log(f"CreateSnipsDialog: שמור snippet חדש: {title}")
                self.accept()
                return True
            return False

        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="שגיאה בשמירת ה-snippet",
                dev_message=str(e),
                severity="ERROR"
            )
            return False

    def _load_category_buttons(self):
        """טוען קטגוריות מקובץ JSON לתוך ה-combobox"""
        categories_file_path = AppPaths.CATEGORYS_JSON
        AppDebugger.log(f"🔄 מנסה לטעון קטגוריות ישירות מהקובץ: {categories_file_path}")
        
        categories_list = []
        try:
            if Path(categories_file_path).exists():
                with open(categories_file_path, 'r', encoding='utf-8') as f:
                    loaded_content = json.load(f)
                
                if isinstance(loaded_content, list):
                    categories_list = loaded_content
                    AppDebugger.log(f"✅ טען {len(categories_list)} קטגוריות מהקובץ.")
                else:
                    AppDebugger.log(f"⚠️ תוכן הקובץ {categories_file_path} אינו רשימה. מתעלם מתוכן הקובץ.")
                    # Optionally, handle this error more severely or create a default list
            else:
                AppDebugger.log(f"⚠️ קובץ הקטגוריות {categories_file_path} לא נמצא. טוען רשימה ריקה.")

        except json.JSONDecodeError as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message=f"שגיאה בפענוח קובץ הקטגוריות: {categories_file_path}",
                dev_message=f"JSON decoding error in {categories_file_path}: {str(e)}",
                severity="ERROR",
                show_gui=False
            )
        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="שגיאה בטעינת קטגוריות",
                dev_message=f"Error loading categories from file: {str(e)}",
                severity="ERROR",
                show_gui=False
            )

        # עדכון ה-combobox
        try:
            self.cmb_category_spinner.clear()
            if categories_list:
                self.cmb_category_spinner.addItems(categories_list)
                AppDebugger.log(f"✅ עדכן combobox עם {len(categories_list)} קטגוריות.")
            else:
                AppDebugger.log("ℹ️ אין קטגוריות לטעינה ל-combobox.")
        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="שגיאה בעדכון רשימת הקטגוריות",
                dev_message=f"Error updating combobox with categories: {str(e)}",
                severity="ERROR",
                show_gui=False
            )

    def mousePressEvent(self, event):
        """תפיסת לחיצת העכבר על הדיאלוג לצורך גרירה"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """הזעת הדיאלוג כשהעכבר נלחץ"""
        if self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """שחרור העכבר"""
        self.drag_pos = None
        super().mouseReleaseEvent(event)