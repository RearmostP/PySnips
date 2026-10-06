# בניית PySnips עבור Windows

הבנייה מתבצעת ב־Windows מתוך שורש המאגר, עם סביבת Python של הפרויקט:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
pyinstaller --clean --noconfirm PySnips.spec
```

אפשר להפעיל את אותו כלי גם כמודול Python:

```powershell
python -m PyInstaller --clean --noconfirm PySnips.spec
```

התוצאה היא `dist/PySnips/PySnips.exe`, לצד כל התלויות והמשאבים הנדרשים.
יש להפיץ את **כל** תיקיית `dist/PySnips/`, ולא רק את קובץ ההפעלה.

ה־spec משתמש בפריסת onedir הרגילה של PyInstaller, ללא חלון קונסולה,
ובאייקון הקיים. הוא אוסף את כל `assets/`, את קובצי ה־`.ui` תחת `core/ui/`
בנתיביהם המקוריים, ואת `data/system_data/version.json` בלבד מתוך תיקיית הנתונים.
הרחבות Markdown הדינמיות מוגדרות כ־hidden imports; Qt ו־Pygments נאספים
באמצעות ה־hooks הרגילים של PyInstaller.

`PySnips.exe` הוא נקודת הכניסה. התיקייה `_internal/` מכילה את Python, Qt,
התלויות ומשאבי האפליקציה, כולל `assets/`, קובצי `core/ui/` ו־
`data/system_data/version.json`. המשאבים נפתרים ביחס ל־`sys._MEIPASS`,
בנפרד מתיקיית קובץ ההפעלה.

נתוני משתמש ומטמון אינם כלולים בבנייה. בהפעלה ארוזה הם נשמרים תחת
`%LOCALAPPDATA%\PySnips\user_data` ו־`%LOCALAPPDATA%\PySnips\cache`.
לבדיקת הפעלה עם נתונים מבודדים:

```powershell
$env:PYSNIPS_DATA_DIR = Join-Path $env:TEMP 'PySnips-build-smoke'
.\dist\PySnips\PySnips.exe
```

`build/` ו־`dist/` הם פלט שניתן לבנות מחדש ואינם נשמרים ב־Git.

## שלב שני: מתקין Windows

לאחר בניית PyInstaller, יש לקמפל את `installer.iss` באמצעות Inno Setup 6.3
ומעלה. משורש המאגר, לדוגמה כשהמהדר מותקן במיקום הרגיל:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' installer.iss
```

אם `ISCC.exe` נמצא ב־PATH, אפשר להשתמש ב־`ISCC.exe installer.iss`.
התוצאה היא `dist/installer/PySnips-0.1.0-Setup.exe`, המכילה את כל
`dist/PySnips/`, כולל `_internal/`. הפלט כבר מוחרג מ־Git.

לפני בניית גרסה חדשה, יש לעדכן את `AppVersion` היחיד ב־`installer.iss`
בהתאם ל־`data/system_data/version.json`, ולבנות מחדש את חבילת PyInstaller.
אין לשנות את ה־AppId הקבוע בין גרסאות.

המתקין אינו דורש הרשאות מנהל ומתקין ל־`%LOCALAPPDATA%\Programs\PySnips`.
הוא יוצר קיצור בתפריט ההתחלה, מציע קיצור שולחן עבודה שאינו מסומן כברירת מחדל,
ומאפשר לבחור הפעלה בסיום. עדכון משתמש באותה זהות התקנה ובאותה תיקייה.
מסיר ההתקנה מסיר קובצי התקנה וקיצורים; הוא משאיר את נתוני המשתמש והמטמון
תחת `%LOCALAPPDATA%\PySnips` ללא שינוי.

המתקין אינו חתום בשלב זה. יצירת GitHub Release וקובץ checksum היא שלב נפרד.
