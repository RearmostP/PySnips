from pathlib import Path


class AppPaths:
    PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

    # ----------------- assets --------------------------
    ASSETS_DIR = PROJECT_DIR / "assets"
    ICONS_DIR = ASSETS_DIR / "icons"

    # ----------------- core -----------------------------
    CORE_DIR = PROJECT_DIR / "core"
    COMMON_DIR = CORE_DIR / "common"

    # ----------------- data -----------------------------
    DATA_DIR = PROJECT_DIR / "data"

    # ----------------- user_data -------------------------
    USERS_DATA_DIR = DATA_DIR / "user_data"
    SNIPS_DATA_DIR = USERS_DATA_DIR / "snips"
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

        # ------ data -----------
        DATA_DIR: True,

        # ------ user_data ------
        USERS_DATA_DIR: True,
        SNIPS_DATA_DIR: True,
        READY_CODE_DATA_DIR: False,

        # ------ system_data ----
        SYSTEM_DATA_DIR: False,

        # ------ ui -------------
        UI_DIR: True,

        # ------ Companion ------
        LOGS_DIR: False,
    }