# =====================================================================
#  מפות הרכיבים וחתימת הזמן (נוצר אוטומטית על ידי Integrity System)
# =====================================================================

UI_TIMESTAMPS = {
    "create_snips_dialog.ui": "2026-06-23 14:25:25",
    "home_screen.ui": "2026-06-21 16:27:49",
    "ready_code_screen.ui": "2026-06-14 03:18:18",
    "snippets_screen.ui": "2026-06-23 14:28:44"
}

class CreateSnipsDialogElements:
    """רכיבים דינמיים עבור create_snips_dialog.ui"""
    BTN_LIST = "btn_List"
    BTN_BOLD = "btn_bold"
    BTN_CANCEL = "btn_cancel"
    BTN_CODE_BLOCK = "btn_code_block"
    BTN_HEADING = "btn_heading"
    BTN_PREVIEW = "btn_preview"
    BTN_SAVE = "btn_save"
    CMB_CATEGORY_SPINNER = "cmb_category_spinner"
    INP_TAGS_INPUT = "inp_tags_input"
    INP_TITLE_INPUT = "inp_title_input"
    LBL_CONTENT_PREVIEW = "lbl_content_preview"
    TXT_CONTENT_INPUT = "txt_content_input"

class HomeScreenElements:
    """רכיבים דינמיים עבור home_screen.ui"""
    BTN_GO_READY_CODE = "btn_go_ready_code"
    BTN_GO_SNIPPETS = "btn_go_snippets"

class ReadyCodeScreenElements:
    """רכיבים דינמיים עבור ready_code_screen.ui"""
    BTN_BACK_HOME = "btn_back_home"

class SnippetsScreenElements:
    """רכיבים דינמיים עבור snippets_screen.ui"""
    BTN_MENU = "btn_menu"
    BTN_NEW_SNIP = "btn_new_snip"
    BTN_TOGGLE_SIDEBAR = "btn_toggle_sidebar"
    FRM_SIDEBAR_LINE = "frm_sidebar_line"
    INP_SEARCH_BAR = "inp_search_bar"
    LBL_RECENT_TITLE = "lbl_recent_title"
    LST_CATEGORIES = "lst_categories"
    SCL_SNIPS = "scl_snips"
    WDG_MAIN_SNIPS = "wdg_main_snips"
    WDG_SCROLL_AREA_CONTENTS = "wdg_scroll_area_contents"
    WDG_SIDEBAR = "wdg_sidebar"

WIDGET_MAPS = {
    "CreateSnipsDialogElements": [
        "btn_List",
        "btn_bold",
        "btn_cancel",
        "btn_code_block",
        "btn_heading",
        "btn_preview",
        "btn_save",
        "cmb_category_spinner",
        "inp_tags_input",
        "inp_title_input",
        "lbl_content_preview",
        "txt_content_input"
    ],
    "HomeScreenElements": [
        "btn_go_ready_code",
        "btn_go_snippets"
    ],
    "ReadyCodeScreenElements": [
        "btn_back_home"
    ],
    "SnippetsScreenElements": [
        "btn_menu",
        "btn_new_snip",
        "btn_toggle_sidebar",
        "frm_sidebar_line",
        "inp_search_bar",
        "lbl_recent_title",
        "lst_categories",
        "scl_snips",
        "wdg_main_snips",
        "wdg_scroll_area_contents",
        "wdg_sidebar"
    ]
}
