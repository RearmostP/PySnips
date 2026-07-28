from pathlib import Path


class AppPaths:
    PROJECT_DIR = Path(__file__).resolve().parent.parent.parent.parent

    # ----------------- assets --------------------------
    ASSETS_DIR = PROJECT_DIR / "assets"
    FONTS_DIR = ASSETS_DIR / "fonts"
    ICONS_DIR = ASSETS_DIR / "icons"
    APP_ICON = ICONS_DIR / "pysnips-multisize.ico"

    # ----------------- core -----------------------------
    CORE_DIR = PROJECT_DIR / "core"
    TOOLS_DIR = CORE_DIR / "tools"

    #------------------ tools ----------------------------
    COMMON_DIR = TOOLS_DIR / "common"
    SYSTEM_TOOLS_DIR = TOOLS_DIR / "system_tools"
    SEARCH_TOOL_DIR = TOOLS_DIR / "search"
    SETTINGS_TOOL_DIR = TOOLS_DIR / "settings"

    SEARCH_INDEX_DIR = SEARCH_TOOL_DIR / "index"


    # ----------------- data -----------------------------
    DATA_DIR = PROJECT_DIR / "data"

    # ----------------- user_data -------------------------
    USERS_DATA_DIR = DATA_DIR / "user_data"

    # ----------------- system_data ------------------------
    SYSTEM_DATA_DIR = DATA_DIR / "system_data"
    SETTINGS_DATA_DIR = SYSTEM_DATA_DIR / "settings"
    CACHE_DATA_DIR = SYSTEM_DATA_DIR / "cache"
    SNIPPET_HTML_CACHE_DIR = CACHE_DATA_DIR / "snippets_html"
    GENERAL_SETTINGS_JSON = SETTINGS_DATA_DIR / "general_settings.json"
    SNIPS_SETTINGS_JSON = SETTINGS_DATA_DIR / "snips_settings.json"
    READY_CODE_SETTINGS_JSON = SETTINGS_DATA_DIR / "ready_code_settings.json"

    # ----------------- trash_data ------------------------
    USER_TRASH_DIR = USERS_DATA_DIR / "trash"
    SNIPS_TRASH_DIR = USER_TRASH_DIR / "snips"
    READY_CODE_TRASH_DIR = USER_TRASH_DIR / "ready_code"

    # ----------------- snips_data -------------------------
    SNIPS_DATA_DIR = USERS_DATA_DIR / "snips"
    SNIPS_FILES = SNIPS_DATA_DIR / "snips_files"
    CATEGORYS_JSON = SNIPS_DATA_DIR / "categorys.json"

    # ----------------- ready_code_data --------------------
    READY_CODE_DATA_DIR = DATA_DIR / "ready_code"

    # ----------------- ui -------------------------------
    UI_DIR = PROJECT_DIR / "core" / "screens" / "ui"
    UI_LOGIC_DIR = CORE_DIR / "screens" / "ui_logic"
    SETTINGS_UI_DIR = UI_DIR / "settings"
    SETTINGS_PAGES_UI_DIR = SETTINGS_UI_DIR / "pages"
    SETTINGS_GENERAL_UI_DIR = SETTINGS_PAGES_UI_DIR / "general"
    SETTINGS_SNIPS_UI_DIR = SETTINGS_PAGES_UI_DIR / "snips"
    SETTINGS_READY_CODE_UI_DIR = SETTINGS_PAGES_UI_DIR / "ready_code"

    # ----------------- screens ---------------------------
    HOME_SCREEN = str(UI_DIR / "home" / "home_screen.ui")
    SNIPPETS_SCREEN = str(UI_DIR / "snips" / "snippets_screen.ui")
    SETTINGS_DIALOG = str(SETTINGS_UI_DIR / "settings_dialog.ui")
    GENERAL_SETTINGS_PAGE = str(SETTINGS_GENERAL_UI_DIR / "general_settings_page.ui")
    SNIPS_OVERVIEW_PAGE = str(SETTINGS_SNIPS_UI_DIR / "snips_overview_page.ui")
    SNIPS_RESTORE_PAGE = str(SETTINGS_SNIPS_UI_DIR / "snips_restore_page.ui")
    SNIPS_CATEGORIES_PAGE = str(SETTINGS_SNIPS_UI_DIR / "snips_categories_page.ui")
    READY_CODE_SETTINGS_PAGE = str(SETTINGS_READY_CODE_UI_DIR / "ready_code_settings_page.ui")
    CREATE_SNIPS_DIALOG = str(UI_DIR / "snips" / "create_snips_dialog.ui")
    SNIPPET_CARD_UI = str(UI_DIR / "snips" / "widgets" / "snippet_card.ui") # Updated to point to the .ui file
    EDIT_CARD_WIDGET = str(UI_DIR / "snips" / "widgets" / "edit_card.ui")
    SNIPPET_SEARCH_WIDGET = str(UI_DIR / "snips" / "widgets" / "snippet_search_widget.ui")

    READY_CODE_SCREEN = str(UI_DIR / "ready_code" / "ready_code_screen.ui")

    # ----------------- Companion -------------------------
    LOGS_DIR = PROJECT_DIR / "logs"



    # =====================================================================
    #  מפת השלמות של המערכת (נתיב : האם קריטי וחוסם ריצה)
    # =====================================================================
    INTEGRITY_MAP = {
        # ------ assets ---------
        ASSETS_DIR: True,
        ICONS_DIR: True,

        # ------ core -----------
        CORE_DIR: True,
        COMMON_DIR: True,
        SYSTEM_TOOLS_DIR: True,
        SETTINGS_TOOL_DIR: False,

        # ------ data -----------
        DATA_DIR: True,

        # ------ user_data ------
        USERS_DATA_DIR: True,
        USER_TRASH_DIR: False,
        SNIPS_TRASH_DIR: False,
        READY_CODE_TRASH_DIR: False,
        SNIPS_DATA_DIR: True,
        CATEGORYS_JSON: True,
        READY_CODE_DATA_DIR: False,

        # ------ system_data ----
        SYSTEM_DATA_DIR: False,
        SETTINGS_DATA_DIR: False,
        CACHE_DATA_DIR: False,
        SNIPPET_HTML_CACHE_DIR: False,
        GENERAL_SETTINGS_JSON: False,
        SNIPS_SETTINGS_JSON: False,
        READY_CODE_SETTINGS_JSON: False,

        # ------ ui -------------
        UI_DIR: True,
        SETTINGS_UI_DIR: False,
        SETTINGS_PAGES_UI_DIR: False,
        SETTINGS_GENERAL_UI_DIR: False,
        SETTINGS_SNIPS_UI_DIR: False,
        SETTINGS_READY_CODE_UI_DIR: False,

        SNIPPET_CARD_UI: True, # Updated name
        EDIT_CARD_WIDGET: False,
        SNIPPET_SEARCH_WIDGET: False,

        # ------ screens --------
        HOME_SCREEN: True,
        SNIPPETS_SCREEN: True,
        SETTINGS_DIALOG: False,
        GENERAL_SETTINGS_PAGE: False,
        SNIPS_OVERVIEW_PAGE: False,
        SNIPS_RESTORE_PAGE: False,
        SNIPS_CATEGORIES_PAGE: False,
        READY_CODE_SETTINGS_PAGE: False,
        CREATE_SNIPS_DIALOG: True,
        READY_CODE_SCREEN: False,


        # ------ Companion ------
        LOGS_DIR: False,
    }
