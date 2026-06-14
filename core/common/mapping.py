# =====================================================================
#  מפות הרכיבים וחתימת הזמן (נוצר אוטומטית על ידי Integrity System)
# =====================================================================

UI_TIMESTAMPS = {
    "home_screen.ui": "2026-06-14 04:53:08",
    "ready_code_screen.ui": "2026-06-14 03:18:18",
    "snippets_screen.ui": "2026-06-14 03:17:32"
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

WIDGET_MAPS = {
    "HomeScreenElements": [
        "btn_go_ready_code",
        "btn_go_snippets"
    ],
    "ReadyCodeScreenElements": [
        "btn_back_home"
    ],
    "SnippetsScreenElements": [
        "btn_back_home"
    ]
}
