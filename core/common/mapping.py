# =====================================================================
#  מפות הרכיבים וחתימת הזמן (נוצר אוטומטית על ידי Integrity System)
# =====================================================================

UI_TIMESTAMPS = {
    "home_screen.ui": "2026-06-21 16:27:49",
    "ready_code_screen.ui": "2026-06-14 03:18:18",
    "snippets_screen.ui": "2026-06-15 12:25:38"
}

class HomeScreenElements:
    """רכיבים דינמיים עבור home_screen.ui"""
    BTN_GO_READY_CODE = "btn_go_ready_code"
    BTN_GO_SNIPPETS = "btn_go_snippets"

class ReadyCodeScreenElements:
    """רכיבים דינמיים עבור ready_code_screen.ui"""
    BTN_BACK_HOME = "btn_back_home"

class SnippetsScreenElements:
    """רכיבים דינמיים עבור snippets_screen.ui"""
    BTN_BACK_HOME = "btn_back_home"
    BTN_NEW_SNIPS = "btn_new_snips"
    SCL_PREVIEW = "scl_preview"
    SCL_SERCH_ATEGORIES = "scl_serch_ategories"
    SCL_SERCH_CATEGORIES = "scl_serch_categories"
    TXT_SERCH_SNIPS = "txt_serch_snips"
    WDG_CATEGORIES_CONTENT = "wdg_categories_content"

WIDGET_MAPS = {
    "HomeScreenElements": [
        "btn_go_ready_code",
        "btn_go_snippets"
    ],
    "ReadyCodeScreenElements": [
        "btn_back_home"
    ],
    "SnippetsScreenElements": [
        "btn_back_home",
        "btn_new_snips",
        "scl_preview",
        "scl_serch_ategories",
        "scl_serch_categories",
        "txt_serch_snips",
        "wdg_categories_content"
    ]
}
