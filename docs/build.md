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

ה־spec משתמש ב־onedir שטוח (`contents_directory='.'`), ללא חלון קונסולה,
ובאייקון הקיים. הוא אוסף את כל `assets/`, את קובצי ה־`.ui` תחת `core/ui/`
בנתיביהם המקוריים, ואת `data/system_data/version.json` בלבד מתוך תיקיית הנתונים.
הרחבות Markdown הדינמיות מוגדרות כ־hidden imports; Qt ו־Pygments נאספים
באמצעות ה־hooks הרגילים של PyInstaller.

נתוני משתמש ומטמון אינם כלולים בבנייה. בהפעלה ארוזה הם נשמרים תחת
`%LOCALAPPDATA%\PySnips`, בעוד נתוני הגרסה נשארים ליד קובץ ההפעלה.
לבדיקת הפעלה עם נתונים מבודדים:

```powershell
$env:PYSNIPS_DATA_DIR = Join-Path $env:TEMP 'PySnips-build-smoke'
.\dist\PySnips\PySnips.exe
```

`build/` ו־`dist/` הם פלט שניתן לבנות מחדש ואינם נשמרים ב־Git.
שלב זה אינו יוצר מתקין.
