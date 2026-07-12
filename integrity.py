import datetime
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# הזרקה מוקדמת של מצב דבאג
if __name__ == "__main__" and "--debug" not in sys.argv:
    sys.argv.append("--debug")

# ייבוא נתיבי המערכת של האפליקציה
from core.common.app_paths import AppPaths

# קבועי מערכת האכיפה הארכיטקטונית
APPROVED_PREFIXES = {
    "btn": "QPushButton",
    "lbl": "QLabel",
    "inp": "QLineEdit",
    "lst": "QListWidget",
    "cmb": "QComboBox",
    "txt": "QTextEdit",
    "scl": "QScrollArea",
    "wdg": "QWidget",
    "frm": "QFrame"
}

DESIGNER_GENERIC_PREFIXES = [
    "pushButton", "label", "lineEdit", "textEdit", "comboBox", "listWidget",
    "calendarWidget", "stackedWidget", "tabWidget", "tableWidget", "treeWidget",
    "graphicsView", "webView", "listView", "undoView", "spinBox", "doubleSpinBox",
    "timeEdit", "dateEdit", "dateTimeEdit", "dial", "horizontalScrollBar",
    "verticalScrollBar", "horizontalSlider", "verticalSlider", "progressBar"
]


def log_integrity_error(file_name: str, obj_name: str, issue_details: str, solution: str):
    """הדפסת שגיאות קומפילציה מותאמת אישית ישירות לטרמינל"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GRAY = "\033[90m"

    print(f"\n🛑 {RED}{BOLD}[שגיאת קומפילציה במערכת השלמות]{RESET}")
    print(f" {GRAY}{'-' * 70}{RESET}")
    print(f" {BOLD}[קובץ ממשק]:{RESET}    {YELLOW}{file_name}{RESET}")
    print(f" {BOLD}[רכיב פסול]:{RESET}    {RED}{obj_name}{RESET}")
    print(f" {BOLD}[תיאור השגיאה]:{RESET} {issue_details}")
    print(f" {BOLD}[פתרון מוצע]:{RESET}  {solution}")
    print(f" {GRAY}{'-' * 70}{RESET}\n")


def log_integrity_msg(message: str):
    """הדפסת לוגים שוטפים של מערכת השלמות באופן עצמאי"""
    CYAN = "\033[96m"
    RESET = "\033[0m"
    prefix = f"[{CYAN}Integrity System{RESET}]"
    print(f"{prefix} {message}")


def validate_ui_element(obj_name: str, file_name: str) -> bool:
    """בודק את תקינות שם הווידג'ט וחוסם שכתוב של mapping במקרה של הפרת חוקים"""
    if "_" not in obj_name:
        return False

    prefix_raw = obj_name.split("_")[0]
    if prefix_raw in DESIGNER_GENERIC_PREFIXES:
        return False

    # 1. בדיקת מספר צמוד לאות (למשל btn1 במקום btn_1)
    for i in range(len(obj_name) - 1):
        if obj_name[i].isalpha() and obj_name[i + 1].isdigit():
            log_integrity_error(
                file_name=file_name,
                obj_name=obj_name,
                issue_details="האלמנט מכיל מספר הצמוד ישירות לאות ללא הפרדת קו תחתון (_).",
                solution=f"שנה ב-Designer ל-'{obj_name[:i + 1]}_{obj_name[i + 1:]}'"
            )
            return False

    # 2. בדיקת אורך הקידומת (חובה בדיוק 3 אותיות)
    if len(prefix_raw) != 3:
        log_integrity_error(
            file_name=file_name,
            obj_name=prefix_raw,
            issue_details=f"הקידומת '{prefix_raw}' היא באורך {len(prefix_raw)} אותיות (מותר רק 3).",
            solution=f"השתמש באחת מהקידומות המאושרות: {list(APPROVED_PREFIXES.keys())}"
        )
        return False

    # 3. בדיקה אם הקידומת רשומה במערכת
    if prefix_raw not in APPROVED_PREFIXES:
        log_integrity_error(
            file_name=file_name,
            obj_name=prefix_raw,
            issue_details=f"הקידומת '{prefix_raw}' אינה מוכרת במערכת האכיפה הארכיטקטונית.",
            solution=f"הקידומות המותרות הן: {list(APPROVED_PREFIXES.keys())}"
        )
        return False

    return True

def find_widget_usages_in_code(widget_var_name: str, class_name: str) -> list:
    """סורק את כל קובצי הפייתון ומחפש איפה המפתח השתמש בשם המשתנה הישן"""
    usages = []
    search_pattern = f"{class_name}.{widget_var_name}"

    for py_file in AppPaths.PROJECT_DIR.glob("**/*.py"):
        if py_file.name in ["mapping.py", "integrity.py"]:
            continue
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if search_pattern in line:
                        usages.append(
                            f" {py_file.relative_to(AppPaths.PROJECT_DIR)} (שורה {line_num}): `{line.strip()}`")
        except Exception:
            pass
    return usages


class SystemIntegrityCompiler:
    """קומפיילר ומנהל שלמות מערכת האוכף חוקי ארכיטקטורה ומסנכרן את mapping.py"""

    def __init__(self):
        self.mapping_file = AppPaths.COMMON_DIR / "mapping.py"
        self.ui_files = []
        self.custom_widgets = []

        # ניהול מצב הפיתוח והמיפויים
        self.has_errors = False
        self.full_widget_maps = {}
        self.generated_classes_code = ""

    def _collect_monitored_files(self) -> bool:
        """סריקת AppPaths וחלוקת הקבצים הקיימים לפי סוגים. מחזירה True אם נמצאה שגיאה קריטית."""
        for attr_name in dir(AppPaths):
            if attr_name.startswith("__"):
                continue

            attr_value = getattr(AppPaths, attr_name)
            if isinstance(attr_value, (str, Path)):
                path_obj = Path(attr_value)
                if path_obj.exists():
                    if path_obj.suffix == ".ui" and path_obj not in self.ui_files:
                        self.ui_files.append(path_obj)
                    elif path_obj.name == "snippet_card.py" and path_obj not in self.custom_widgets:
                        self.custom_widgets.append(path_obj)
                elif str(attr_value).endswith((".ui", ".py")) and attr_name.isupper():
                    print(f"\n[CRITICAL ERROR] AppPaths.{attr_name} points to a missing path: {path_obj}\n")
                    return True
        return False

    @staticmethod
    def _get_changed_files(all_files: list[Path], current_timestamps: dict) -> list[str]:
        """השוואת חתימות זמן מול המיפוי הישן כדי לאתר קבצים ששונו."""
        changed_files = []
        old_timestamps = {}
        try:
            import core.system_tools.mapping as current_mapping
            old_timestamps = getattr(current_mapping, "UI_TIMESTAMPS", {})
        except Exception:
            pass

        for f in all_files:
            if old_timestamps.get(f.name) != current_timestamps.get(f.name):
                changed_files.append(f.name)
        return changed_files

    def _parse_ui_xml_file(self, ui_file: Path, class_name: str) -> list[str]:
        """ניתוח קובץ XML של מעצב ה-UI ואכיפת חוקי שמות."""
        found_elements = []
        file_name = ui_file.name

        try:
            tree = ET.parse(ui_file)
            root = tree.getroot()

            for widget in root.iter("widget"):
                obj_name = widget.get("name")
                if obj_name:
                    if validate_ui_element(obj_name, file_name):
                        found_elements.append(obj_name)
                    else:
                        if "_" in obj_name:
                            prefix = obj_name.split("_")[0]
                            if prefix not in DESIGNER_GENERIC_PREFIXES:
                                self.has_errors = True

            # בדיקת רכיבים שנמחקו/שונו אך עדיין נמצאים בשימוש בקוד פייתון
            try:
                import core.system_tools.mapping as old_mapping
                old_class = getattr(old_mapping, class_name, None)
                if old_class:
                    old_variables = [attr for attr in dir(old_class) if attr.isupper()]
                    for old_var in old_variables:
                        actual_value = getattr(old_class, old_var)
                        if actual_value not in found_elements:
                            code_usages = find_widget_usages_in_code(old_var, class_name)
                            if code_usages:
                                usages_str = "\n".join(code_usages)
                                log_integrity_error(
                                    file_name=file_name,
                                    obj_name=actual_value,
                                    issue_details=f"הרכיב שונה או נמחק ב-Designer, אך שם המשתנה הישן ({class_name}.{old_var}) עדיין מופיע בקוד!",
                                    solution=f"עדכן או מחק את השורות הבאות בקוד לפני הרצה מחדש:\n{usages_str}"
                                )
                                self.has_errors = True
            except Exception:
                pass

        except Exception as e:
            print(f"\n[CRITICAL ERROR] Failed to parse XML structure for {file_name}. Details: {e}\n")
            self.has_errors = True

        return sorted(set(found_elements))

    def _parse_custom_widget_py_file(self, widget_file: Path) -> list[str]:
        """ניתוח קובץ קוד פייתון של רכיב קסטום ואכיפת חוקי שמות על משתני self."""
        found_elements = []
        file_name = widget_file.name

        try:
            with open(widget_file, "r", encoding="utf-8") as f:
                content = f.read()

            internal_widgets = re.findall(r"self\.([a-zA-Z0-9_]+)", content)

            for obj_name in internal_widgets:
                if "_" in obj_name:
                    prefix = obj_name.split("_")[0]
                    if prefix in APPROVED_PREFIXES:
                        if validate_ui_element(obj_name, file_name):
                            found_elements.append(obj_name)
                        else:
                            self.has_errors = True
                    elif len(prefix) == 3 and prefix not in APPROVED_PREFIXES:
                        validate_ui_element(obj_name, file_name)
                        self.has_errors = True
        except Exception as e:
            print(f"\n[CRITICAL ERROR] Failed to analyze custom widget code for {file_name}. Details: {e}\n")
            self.has_errors = True

        return sorted(set(found_elements))

    def _append_class_source_code(self, class_name: str, elements: list[str], description: str):
        """מחוללת את מחרוזת קוד המקור עבור המחלקה הסטטית ומחברת אותה לפלט המרכזי."""
        code = f"class {class_name}:\n"
        code += f'    """{description}"""\n'
        if not elements:
            code += "    pass\n"
        else:
            for elem in elements:
                code += f'    {elem.upper()} = "{elem}"\n'
        code += "\n"
        self.generated_classes_code += code

    def compile(self):
        """מנוע הסריקה המרכזי - הפונקציה המנהלת שמפעילה את כל שלבי הקומפילציה"""
        log_integrity_msg("מתחיל סריקת שלמות ואכיפת חוקי עיצוב...")

        # 1. איסוף קבצים
        if self._collect_monitored_files():
            return

        # 2. ניהול חתימות זמן ושינויים
        all_monitored_files = self.ui_files + self.custom_widgets
        current_timestamps = {
            f.name: datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M:%S')
            for f in all_monitored_files
        }
        changed_files = self._get_changed_files(all_monitored_files, current_timestamps)

        # 3. עיבוד קובצי UI (XML)
        for ui_file in self.ui_files:
            class_name = "".join([part.capitalize() for part in ui_file.stem.split("_")]) + "Elements"
            elements = self._parse_ui_xml_file(ui_file, class_name)

            self.full_widget_maps[class_name] = elements
            self._append_class_source_code(
                class_name=class_name,
                elements=elements,
                description=f"רכיבים דינמיים עבור {ui_file.name}"
            )

        # 4. עיבוד קובצי רכיבים קסטום (Python)
        for widget_file in self.custom_widgets:
            class_name = "".join([part.capitalize() for part in widget_file.stem.split("_")]) + "Elements"
            elements = self._parse_custom_widget_py_file(widget_file)

            self.full_widget_maps[class_name] = elements
            self._append_class_source_code(
                class_name=class_name,
                elements=elements,
                description=f"רכיבים פנימיים מתוך קוד הרכיב הקסטום {widget_file.name}"
            )

        # 5. בדיקת חסימה וכתיבה סופית לדיסק
        if self.has_errors:
            print("\n[COMPILATION ABORTED] Integrity system blocked mapping.py rewrite due to architectural errors.\n")
            return

        if changed_files:
            log_integrity_msg(f"זוהו שינויים ברכיבים עבור: {', '.join(changed_files)}")
        else:
            log_integrity_msg("לא זוהו שינויים חדשים ברכיבים.")

        timestamps_pretty = json.dumps(current_timestamps, indent=4)
        maps_pretty = json.dumps(self.full_widget_maps, indent=4)

        final_mapping_content = (
            "# =====================================================================\n"
            "#  מפות הרכיבים וחתימת הזמן (נוצר אוטומטית על ידי Integrity System)\n"
            "# =====================================================================\n\n"
            f"UI_TIMESTAMPS = {timestamps_pretty}\n\n"
            f"{self.generated_classes_code}"
            f"WIDGET_MAPS = {maps_pretty}\n"
        )

        try:
            with open(self.mapping_file, "w", encoding="utf-8") as f:
                f.write(final_mapping_content)
            log_integrity_msg("🎉 קובץ mapping.py שוכתב ועודכן בהצלחה! המערכת יציבה ומסונכרנת.")
        except Exception as e:
            print(f"\n[CRITICAL ERROR] Failed to write static mapping file to {self.mapping_file}. Error: {e}\n")


if __name__ == "__main__":
    compiler = SystemIntegrityCompiler()
    compiler.compile()