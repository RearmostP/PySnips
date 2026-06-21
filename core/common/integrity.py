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

#  הזרקה מוקדמת: מוודאים שמצב דבאג פעיל עוד לפני ייבוא הלוגר
if __name__ == "__main__" and "--debug" not in sys.argv:
    sys.argv.append("--debug")

import os
from datetime import datetime
import json
import xml.etree.ElementTree as ET

from core.common.app_paths import AppPaths
from core.common.error_manager import AppErrorHandler, AppDebugger

APPROVED_PREFIXES = {
    "btn": "QPushButton",
    "lbl": "QLabel",
    "inp": "QLineEdit",
    "lst": "QListWidget",
    "cmb": "QComboBox",
    "txt": "QTextEdit",
    "scl": "QScrollArea",
    "wdg": "QWidget"
}

DESIGNER_GENERIC_PREFIXES = [
    "pushButton", "label", "lineEdit", "textEdit", "comboBox", "listWidget",
    "calendarWidget", "stackedWidget", "tabWidget", "tableWidget", "treeWidget",
    "graphicsView", "webView", "listView", "undoView", "spinBox", "doubleSpinBox",
    "timeEdit", "dateEdit", "dateTimeEdit", "dial", "horizontalScrollBar",
    "verticalScrollBar", "horizontalSlider", "verticalSlider", "progressBar"
]

POLICY_GUIDE = (
    " ספר החוקים לשמות ווידג'טים ב-PySnips:\n"
    f"  1. חובה להשתמש בקידומת מאושרת בת 3 אותיות מתוך הרשימה: {list(APPROVED_PREFIXES.keys())}\n"
    "  2. חובה לשים קו תחתון (_) מיד אחרי הקידומת (למשל: btn_).\n"
    "  3. אסור להצמיד מספרים לאותיות! חובה להפריד מספרים עם קו תחתון (למשל: btn_snippet_1 ולא btn_snippet1).\n"
    "  4. שמות אוטומטיים של ה-Designer יסוננו אוטומטית."
)


def validate_ui_element(obj_name: str, file_name: str) -> bool:
    """בודק את תקינות שם הווידג'ט ומציג שגיאות מפורטות במערכת השגיאות המובנית"""
    if "_" not in obj_name:
        return False

    prefix_raw = obj_name.split("_")[0]
    if prefix_raw in DESIGNER_GENERIC_PREFIXES:
        return False

    # בדיקת מספר צמוד לאות
    for i in range(len(obj_name) - 1):
        if obj_name[i].isalpha() and obj_name[i + 1].isdigit():
            AppErrorHandler.handle_error(
                user_message=f"שגיאת מבנה חמורה בקובץ ממשק המשתמש: {file_name}",
                dev_message=f"האלמנט '{obj_name}' מכיל מספר הצמוד ישירות לאות ללא הפרדת קו תחתון (_).",
                severity="ERROR",
                solution_hint=f"{POLICY_GUIDE}\n\nתיקון מוצע: שנה ב-Designer ל-'{obj_name[:i+1]}_{obj_name[i+1:]}'"
            )
            return False

    if len(prefix_raw) != 3:
        AppErrorHandler.handle_error(
            user_message=f"שגיאת אכיפת קידומת בקובץ ממשק המשתמש: {file_name}",
            dev_message=f"האלמנט '{obj_name}' משתמש בקידומת '{prefix_raw}' שאורכה {len(prefix_raw)} אותיות (מותר רק 3).",
            severity="ERROR",
            solution_hint=POLICY_GUIDE
        )
        return False

    if prefix_raw not in APPROVED_PREFIXES:
        AppErrorHandler.handle_error(
            user_message=f"שגיאת קיצור לא מוכר בקובץ ממשק המשתמש: {file_name}",
            dev_message=f"הקידומת '{prefix_raw}' שנמצאה באלמנט '{obj_name}' אינה רשומה בפורמט המערכת המאושר.",
            severity="ERROR",
            solution_hint=POLICY_GUIDE
        )
        return False

    return True


def find_widget_usages_in_code(widget_var_name: str, class_name: str) -> list:
    """סורק את כל קובצי הפייתון ומחפש איפה המתכנת השתמש בשם המשתנה הישן"""
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
    """מנוע הסריקה המרכזי - בודק שלמות ומשכתב אך ורק את קובץ mapping.py"""
    # הדפסת לוג קבוע - מועבר כהודעה קריטית או ישירה ללוגר כדי שיופיע תמיד
    AppDebugger.log(" [Integrity System] מתחיל סריקת שלמות ואכיפת חוקי עיצוב...")

    ui_dir = AppPaths.UI_DIR
    mapping_file = AppPaths.COMMON_DIR / "mapping.py"

    if not ui_dir.exists():
        AppErrorHandler.handle_error(
            user_message="שגיאת מערכת: תיקיית ה-UI לא נמצאה.",
            dev_message=f"לא ניתן לבצע בדיקת קומפילציה ואכיפה משום שהנתיב חסר פיזית בדיסק: {ui_dir}",
            severity="CRITICAL",
            solution_hint="וודא שתיקיית קובצי העיצוב קיימת במיקום המוגדר תחת AppPaths."
        )
        return

    ui_files = list(ui_dir.glob("*.ui"))
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
                                AppErrorHandler.handle_error(
                                    user_message=f"חסימת קומפילציה: רכיב שונה בדיזיינר אך נמצא בשימוש בקוד הפייתון!",
                                    dev_message=(
                                        f"שינית שם או מחקת ב-Designer את הרכיב: '{actual_value}'\n"
                                        f"שם המשתנה הישן שעדיין רשום בקוד: {class_name}.{old_var}\n"
                                        f"נתיבי שימוש שנמצאו בפרויקט:\n{usages_str}"
                                    ),
                                    severity="CRITICAL",
                                    solution_hint="עדכן או מחק את השורות המצוינות בקובצי הפייתון לפני הרצה מחדש של ה-Integrity."
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
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message=f"שגיאה קריטית בפענוח מבנה הקובץ {file_name}",
                dev_message=f"מנוע ה-Integrity נכשל בקריאת מבנה ה-XML של הקובץ: {ui_file}",
                severity="CRITICAL"
            )
            has_errors = True

    if has_errors:
        AppErrorHandler.handle_error(
            user_message="הקומפילציה והשכתוב בוטלו!",
            dev_message="המערכת מנעה את עדכון קובץ המיפוי עקב שגיאות שמות או חוסר סנכרון מול קוד הפייתון.",
            severity="ERROR"
        )
        return

    if changed_files:
        AppDebugger.log(f" זוהו שינויים בדיזיינר עבור: {', '.join(changed_files)}")
    else:
        AppDebugger.log(" לא זוהו שינויים חדשים בדיזיינר.")

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
        AppDebugger.log("🎉 קובץ mapping.py שוכתב ועודכן בהצלחה! המערכת יציבה ומסונכרנת.")
    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="נכשלה כתיבת קובץ המיפוי הסטטי.",
            dev_message=f"לא ניתן לשמור שינויים פיזיים לתוך קובץ היעד: {mapping_file}",
            severity="CRITICAL"
        )


if __name__ == "__main__":
    compile_system_integrity()