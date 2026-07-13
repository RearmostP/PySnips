# =====================================================================
#  מפות הרכיבים וחתימת הזמן (נוצר אוטומטית על ידי Integrity System)
# =====================================================================

UI_TIMESTAMPS = {
    "create_snips_dialog.ui": "2026-07-12 12:11:59",
    "edit_card.ui": "2026-07-12 06:12:07",
    "home_screen.ui": "2026-06-21 16:27:49",
    "ready_code_screen.ui": "2026-06-14 03:18:18",
    "snippets_screen.ui": "2026-06-24 15:33:03",
    "snippet_card.ui": "2026-07-12 17:01:50",
    "snippet_search_widget.ui": "2026-07-13 10:24:08"
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

class EditCardElements:
    """רכיבים דינמיים עבור edit_card.ui"""
    BTN_CANCEL_EDIT = "btn_cancel_edit"
    BTN_SAVE_EDIT = "btn_save_edit"
    TXT_SNIPPET_CONTENT = "txt_snippet_content"

class HomeScreenElements:
    """רכיבים דינמיים עבור home_screen.ui"""
    BTN_GO_READY_CODE = "btn_go_ready_code"
    BTN_GO_SNIPPETS = "btn_go_snippets"

class ReadyCodeScreenElements:
    """רכיבים דינמיים עבור ready_code_screen.ui"""
    BTN_BACK_HOME = "btn_back_home"

class SnippetsScreenElements:
    """רכיבים דינמיים עבור snippets_screen.ui"""
    BTN_ADD_CATEGORY = "btn_add_category"
    BTN_MENU = "btn_menu"
    BTN_NEW_SNIPPET = "btn_new_snippet"
    FRM_SPLITTER = "frm_splitter"
    INP_SEARCH_SNIPS = "inp_search_snips"
    LBL_APP_NAME = "lbl_app_name"
    LBL_CATEGORY_TITLE = "lbl_category_title"
    SCL_CATEGORIES = "scl_categories"
    SCL_SNIPPETS = "scl_snippets"
    WDG_MAIN_CONTENT = "wdg_main_content"
    WDG_SIDEBAR = "wdg_sidebar"

class SnippetCardElements:
    """רכיבים דינמיים עבור snippet_card.ui"""
    BTN_DETAILS = "btn_details"
    BTN_EDIT = "btn_edit"
    LBL_TITLE_LABEL = "lbl_title_label"
    TXT_CONTENT_PREVIEW = "txt_content_preview"

class SnippetSearchWidgetElements:
    """רכיבים דינמיים עבור snippet_search_widget.ui"""
    BTN_LOAD_MORE = "btn_load_more"
    LBL_STATUS = "lbl_status"

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
    "EditCardElements": [
        "btn_cancel_edit",
        "btn_save_edit",
        "txt_snippet_content"
    ],
    "HomeScreenElements": [
        "btn_go_ready_code",
        "btn_go_snippets"
    ],
    "ReadyCodeScreenElements": [
        "btn_back_home"
    ],
    "SnippetsScreenElements": [
        "btn_add_category",
        "btn_menu",
        "btn_new_snippet",
        "frm_splitter",
        "inp_search_snips",
        "lbl_app_name",
        "lbl_category_title",
        "scl_categories",
        "scl_snippets",
        "wdg_main_content",
        "wdg_sidebar"
    ],
    "SnippetCardElements": [
        "btn_details",
        "btn_edit",
        "lbl_title_label",
        "txt_content_preview"
    ],
    "SnippetSearchWidgetElements": [
        "btn_load_more",
        "lbl_status"
    ]
}
