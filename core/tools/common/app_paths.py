from pathlib import Path


class AppPaths:
    PROJECT_DIR = Path(__file__).resolve().parent.parent.parent.parent

    # ----------------- assets --------------------------
    ASSETS_DIR = PROJECT_DIR / "assets"
    FONTS_DIR = ASSETS_DIR / "fonts"
    ICONS_DIR = ASSETS_DIR / "icons"

    # ----------------- core -----------------------------
    CORE_DIR = PROJECT_DIR / "core"
    TOOLS_DIR = CORE_DIR / "tools"

    #------------------ tools ----------------------------
    COMMON_DIR = TOOLS_DIR / "common"
    SYSTEM_TOOLS_DIR = TOOLS_DIR / "system_tools"
    SEARCH_TOOL_DIR = TOOLS_DIR / "search"

    SEARCH_INDEX_DIR = SEARCH_TOOL_DIR / "index"


    # ----------------- data -----------------------------
    DATA_DIR = PROJECT_DIR / "data"

    # ----------------- user_data -------------------------
    USERS_DATA_DIR = DATA_DIR / "user_data"

    # ----------------- snips_data -------------------------
    SNIPS_DATA_DIR = USERS_DATA_DIR / "snips"
    SNIPS_FILES = SNIPS_DATA_DIR / "snips_files"
    CATEGORYS_JSON = SNIPS_DATA_DIR / "categorys.json"

    # ----------------- ready_code_data --------------------
    READY_CODE_DATA_DIR = DATA_DIR / "ready_code"

    # ----------------- system_data ------------------------
    SYSTEM_DATA_DIR = DATA_DIR / "system_data"

    # ----------------- ui -------------------------------
    UI_DIR = PROJECT_DIR / "core" / "screens" / "ui"
    UI_LOGIC_DIR = CORE_DIR / "screens" / "ui_logic"

    # ----------------- screens ---------------------------
    HOME_SCREEN = str(UI_DIR / "home" / "home_screen.ui")
    SNIPPETS_SCREEN = str(UI_DIR / "snips" / "snippets_screen.ui")
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

        # ------ data -----------
        DATA_DIR: True,

        # ------ user_data ------
        USERS_DATA_DIR: True,
        SNIPS_DATA_DIR: True,
        CATEGORYS_JSON: True,
        READY_CODE_DATA_DIR: False,

        # ------ system_data ----
        SYSTEM_DATA_DIR: False,

        # ------ ui -------------
        UI_DIR: True,

        SNIPPET_CARD_UI: True, # Updated name
        EDIT_CARD_WIDGET: False,
        SNIPPET_SEARCH_WIDGET: False,

        # ------ screens --------
        HOME_SCREEN: True,
        SNIPPETS_SCREEN: True,
        CREATE_SNIPS_DIALOG: True,
        READY_CODE_SCREEN: False,


        # ------ Companion ------
        LOGS_DIR: False,
    }
