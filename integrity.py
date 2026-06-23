"""
🛡️ PySnips 0.4 - System Integrity Testing System (The Compiler)
==================================================================

🎯 תפקיד המערכת (System Role):
-------------------------------
קובץ זה מתפקד כ"קומפיילר" חכם פנימי של האפליקציה, שתפקידו לאכוף את חוקי העיצוב והארכיטקטורה
של הפרויקט בשלבי הפיתוח. המערכת מונעת מהמתכנת לבצע טעויות שמות (Naming Conventions) ב-Qt Designer,
וחוסמת את האפליקציה מהרצה במידה ושינוי שם של רכיב בממשק עלול לשבור את קוד הפייתון הקיים.
המערכת מוודאת סנכרון מוחלט ומפיקה קובץ מיפוי סטטי (mapping.py) נקי ונטול פונקציות.

🧰 ארגז הכלים הקיים בקובץ (Developer Tools Included):
-------------------------------------------------------
1. מערכת אכיפת הקידומות (Naming Policy Enforcer):
   מנגנון המבוסס על רשימת APPROVED_PREFIXES המאשר רק קידומות תקניות בנות 3 אותיות (כמו btn, lbl).

2. מסנן רכיבים גנריים (Designer Trash Filter):
   רשימה שחורה (DESIGNER_GENERIC_PREFIXES) שמסננת ומתעלמת בשקט מרכיבים אוטומטיים של ה-Designer
   שלא שונה שמם (כמו pushButton_1), כדי לא להציק למפתח בהודעות שגיאה מיותרות.

3. סורק מבנה השמות (Syntax Validator):
   פונקציית validate_ui_element המזהה שגיאות מבניות קריטיות (כמו הצמדת מספר לאות ללא קו תחתון, btn1).

4. מאתר שימוש בקוד (Static Code Usage Tracker):
   פונקציית find_widget_usages_in_code הסורקת באופן טקסטואלי את כל קובצי ה-py. בפרויקט ומאתרת
   האם משתנה ישן שעומד להימחק עדיין נמצא בשימוש איפשהו בקוד, ומציגה למפתח מיקום ושורה מדויקים.

5. מחולל קוד המיפוי (Code Generator & Mapper):
   פונקציית compile_system_integrity שמפרקת את ה-XML של ה-UI, יוצרת קלאסים מסודרים עם משתנים קבועים,
   ומייצרת את מפת הגישה הדינמית WIDGET_MAPS עבור האפליקציה.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
import xml.etree.ElementTree as ET

# הזרקה מוקדמת: מוודאים שמצב דבאג פעיל עוד לפני ייבוא הרכיבים
if __name__ == "__main__" and "--debug" not in sys.argv:
    sys.argv.append("--debug")

# ייבוא נתיבים בלבד - ללא מערכת השגיאות של האפליקציה
from core.common.app_paths import AppPaths

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
    """הדפסת שגיאות קומפילציה מותאמת אישית ישירות לטרמינל ללא תלות באפליקציה"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GRAY = "\033[90m"

    print(f"\n🛑 {RED}{BOLD}[שגיאת קומפילציה במערכת השלמות]{RESET}")
    print(f" {GRAY}{'-'*70}{RESET}")
    print(f" {BOLD}[קובץ ממשק]:{RESET}    {YELLOW}{file_name}{RESET}")
    print(f" {BOLD}[רכיב פסול]:{RESET}    {RED}{obj_name}{RESET}")
    print(f" {BOLD}[תיאור השגיאה]:{RESET} {issue_details}")
    print(f" {BOLD}[פתרון מוצע]:{RESET}  {solution}")
    print(f" {GRAY}{'-'*70}{RESET}\n")


def log_integrity_msg(message: str, is_debug: bool = True):
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
                solution=f"שנה ב-Designer ל-'{obj_name[:i+1]}_{obj_name[i+1:]}'"
            )
            return False

    # 2. בדיקת אורך הקידומת (חובה בדיוק 3 אותיות)
    if len(prefix_raw) != 3:
        log_integrity_error(
            file_name=file_name,
            obj_name=obj_name,
            issue_details=f"הקידומת '{prefix_raw}' היא באורך {len(prefix_raw)} אותיות (מותר רק 3).",
            solution=f"השתמש באחת מהקידומות המאושרות: {list(APPROVED_PREFIXES.keys())}"
        )
        return False

    # 3. בדיקה אם הקידומת רשומה במערכת
    if prefix_raw not in APPROVED_PREFIXES:
        log_integrity_error(
            file_name=file_name,
            obj_name=obj_name,
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
                        usages.append(f" {py_file.relative_to(AppPaths.PROJECT_DIR)} (שורה {line_num}): `{line.strip()}`")
        except Exception:
            pass
    return usages


def compile_system_integrity():
    """מנוע הסריקה המרכזי - אוסף קבצים מ-AppPaths, בודק שלמות ומשכתב את mapping.py"""
    log_integrity_msg("מתחיל סריקת שלמות ואכיפת חוקי עיצוב...")

    mapping_file = AppPaths.COMMON_DIR / "mapping.py"

    # איסוף קובצי ה-UI ישירות מתוך המשתנים של AppPaths
    ui_files = []
    for attr_name in dir(AppPaths):
        if attr_name.startswith("__"):
            continue

        attr_value = getattr(AppPaths, attr_name)
        if isinstance(attr_value, (str, Path)) and str(attr_value).endswith(".ui"):
            ui_path = Path(attr_value)
            if ui_path.exists():
                if ui_path not in ui_files:
                    ui_files.append(ui_path)
            else:
                print(f"\n❌ [שגיאה קריטית] המשתנה AppPaths.{attr_name} מצביע לנתיב חסר בדיסק: {ui_path}\n")
                return

    current_timestamps = {
        f.name: datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M:%S')
        for f in ui_files
    }

    old_timestamps = {}
    try:
        import core.common.mapping as current_mapping
        old_timestamps = getattr(current_mapping, "UI_TIMESTAMPS", {})
    except Exception:
        pass

    has_errors = False
    changed_files = []
    full_widget_maps = {}
    generated_classes_code = ""

    for ui_file in ui_files:
        file_name = ui_file.name
        class_name = "".join([part.capitalize() for part in ui_file.stem.split("_")]) + "Elements"

        if old_timestamps.get(file_name) != current_timestamps.get(file_name):
            changed_files.append(file_name)

        try:
            tree = ET.parse(ui_file)
            root = tree.getroot()
            found_elements = []

            for widget in root.iter("widget"):
                obj_name = widget.get("name")
                if obj_name:
                    if validate_ui_element(obj_name, file_name):
                        found_elements.append(obj_name)
                    else:
                        if "_" in obj_name:
                            prefix = obj_name.split("_")[0]
                            if prefix not in DESIGNER_GENERIC_PREFIXES:
                                has_errors = True

            # בדיקה אם רכיב שונה או נמחק בדיזיינר אך עדיין קיים בקוד פייתון
            try:
                import core.common.mapping as old_mapping
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
                                has_errors = True
            except Exception:
                pass

            sorted_elements = sorted(set(found_elements))
            full_widget_maps[class_name] = sorted_elements

            generated_classes_code += f"class {class_name}:\n"
            generated_classes_code += f'    """רכיבים דינמיים עבור {file_name}"""\n'
            if not sorted_elements:
                generated_classes_code += "    pass\n"
            else:
                for elem in sorted_elements:
                    generated_classes_code += f'    {elem.upper()} = "{elem}"\n'
            generated_classes_code += "\n"

        except Exception as e:
            print(f"\n❌ [שגיאה קריטית] נכשלה קריאת מבנה ה-XML של הקובץ {file_name}. פירוט: {e}\n")
            has_errors = True

    if has_errors:
        print("\n🛑 [קומפילציה בוטלה] המערכת מנעה את שכתוב קובץ המיפוי עקב שגיאות מבנה או חוסר סנכרון.\n")
        return

    if changed_files:
        log_integrity_msg(f"זוהו שינויים בדיזיינר עבור: {', '.join(changed_files)}")
    else:
        log_integrity_msg("לא זוהו שינויים חדשים בדיזיינר.")

    timestamps_pretty = json.dumps(current_timestamps, indent=4)
    maps_pretty = json.dumps(full_widget_maps, indent=4)

    final_mapping_content = (
        "# =====================================================================\n"
        "#  מפות הרכיבים וחתימת הזמן (נוצר אוטומטית על ידי Integrity System)\n"
        "# =====================================================================\n\n"
        f"UI_TIMESTAMPS = {timestamps_pretty}\n\n"
        f"{generated_classes_code}"
        f"WIDGET_MAPS = {maps_pretty}\n"
    )

    try:
        with open(mapping_file, "w", encoding="utf-8") as f:
            f.write(final_mapping_content)
        log_integrity_msg("🎉 קובץ mapping.py שוכתב ועודכן בהצלחה! המערכת יציבה ומסונכרנת.")
    except Exception as e:
        print(f"\n❌ [שגיאה קריטית] נכשלה כתיבת קובץ המיפוי הסטטי אל {mapping_file}. שגיאה: {e}\n")


if __name__ == "__main__":
    compile_system_integrity()