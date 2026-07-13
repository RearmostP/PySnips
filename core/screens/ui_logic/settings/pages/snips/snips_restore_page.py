# תפקיד הקובץ:
# לוגיקת עמוד שחזור השליפים בחלון ההגדרות.
# העמוד מציג את הגדרות אשפת השליפים, מאפשר לשמור אותן, מציג שליפים שנמחקו,
# ומאפשר לבחור פריטים לשחזור או למחיקה לצמיתות.

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QMessageBox, QWidget

from core.tools.common.app_paths import AppPaths
from core.tools.common.dynamic_ui_loader import create_dynamic_ui_loader
from core.tools.common.error_manager import AppErrorHandler
from core.tools.search.snippet_search_engine import SnippetSearchEngine
from core.tools.snips.snippet_trash_manager import (
    list_deleted_snippets,
    permanently_delete_trash_item,
    restore_trash_item,
)
from core.tools.settings.snips_settings import (
    SnipsTrashSettings,
    load_snips_trash_settings,
    save_snips_trash_settings,
)


class SnipsRestorePage(create_dynamic_ui_loader(AppPaths.SNIPS_RESTORE_PAGE)):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selection_mode = False
        self.selection_actions_widget = self._resolve_selection_actions_widget()
        self.setup_ui()
        self.setup_events()
        self.load_settings()
        self.refresh_trash_items()

    def get_view(self) -> QWidget:
        return self

    def setup_ui(self) -> None:
        self.lbl_trash_items_title.setVisible(False)
        self._set_selection_actions_visible(False)
        self.btn_restore_selected.setEnabled(False)
        self.btn_delete_selected.setEnabled(False)
        self.lbl_settings_status.clear()
        self.apply_styles()

    def setup_events(self) -> None:
        self.btn_save_trash_settings.clicked.connect(self.save_settings)
        self.btn_select_trash_items.clicked.connect(self.enable_selection_mode)
        self.btn_cancel_selection.clicked.connect(self.disable_selection_mode)
        self.btn_restore_selected.clicked.connect(self.restore_selected_items)
        self.btn_delete_selected.clicked.connect(self.delete_selected_items)
        self.lst_trash_snippets.itemChanged.connect(self.update_selection_actions)

    def load_settings(self) -> None:
        settings = load_snips_trash_settings()
        self.inp_retention_days.setValue(settings.retention_days)
        self.btn_delete_permanently.setChecked(settings.delete_permanently)

    def save_settings(self) -> None:
        settings = SnipsTrashSettings(
            retention_days=self.inp_retention_days.value(),
            delete_permanently=self.btn_delete_permanently.isChecked(),
        )
        if save_snips_trash_settings(settings):
            self.lbl_settings_status.setText("נשמר")
        else:
            self.lbl_settings_status.setText("שמירה נכשלה")

    def refresh_trash_items(self) -> None:
        self.lst_trash_snippets.blockSignals(True)
        self.lst_trash_snippets.clear()

        trash_items = list_deleted_snippets()
        self.btn_select_trash_items.setVisible(bool(trash_items) and not self.selection_mode)
        if not trash_items:
            empty_item = QListWidgetItem("אין שליפים באשפה")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.lst_trash_snippets.addItem(empty_item)
        else:
            for trash_record in trash_items:
                item = QListWidgetItem(self._format_trash_item_text(trash_record))
                item.setData(Qt.ItemDataRole.UserRole, trash_record.get("trash_dir"))
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                if self.selection_mode:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Unchecked)
                self.lst_trash_snippets.addItem(item)

        self.lst_trash_snippets.blockSignals(False)
        self.update_selection_actions()

    def enable_selection_mode(self) -> None:
        self.selection_mode = True
        self._set_selection_actions_visible(True)
        self.btn_select_trash_items.setVisible(False)
        self.refresh_trash_items()

    def disable_selection_mode(self) -> None:
        self.selection_mode = False
        self._set_selection_actions_visible(False)
        self.btn_select_trash_items.setVisible(True)
        self.refresh_trash_items()

    def update_selection_actions(self) -> None:
        selected_count = len(self._selected_trash_dirs())
        has_selection = selected_count > 0
        self.btn_restore_selected.setEnabled(has_selection)
        self.btn_delete_selected.setEnabled(has_selection)

    def restore_selected_items(self) -> None:
        selected_trash_dirs = self._selected_trash_dirs()
        if not selected_trash_dirs:
            return

        restored_count = sum(1 for trash_dir in selected_trash_dirs if restore_trash_item(trash_dir))
        if restored_count:
            self._rebuild_search_index()
        self.lbl_settings_status.setText(f"שוחזרו {restored_count} שליפים")
        self.disable_selection_mode()

    def delete_selected_items(self) -> None:
        selected_trash_dirs = self._selected_trash_dirs()
        if not selected_trash_dirs:
            return

        result = QMessageBox.question(
            self,
            "מחיקה לצמיתות",
            "למחוק את השליפים שנבחרו לצמיתות? לא ניתן לשחזר פעולה זו.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        deleted_count = sum(1 for trash_dir in selected_trash_dirs if permanently_delete_trash_item(trash_dir))
        self.lbl_settings_status.setText(f"נמחקו {deleted_count} שליפים")
        self.disable_selection_mode()

    def _selected_trash_dirs(self) -> list[str]:
        selected_trash_dirs = []
        for index in range(self.lst_trash_snippets.count()):
            item = self.lst_trash_snippets.item(index)
            trash_dir = item.data(Qt.ItemDataRole.UserRole)
            if not trash_dir:
                continue
            if item.checkState() == Qt.CheckState.Checked:
                selected_trash_dirs.append(str(trash_dir))
        return selected_trash_dirs

    def _resolve_selection_actions_widget(self) -> QWidget | None:
        widget = getattr(self, "selection_actions_widget", None)
        if widget is not None:
            return widget

        widget = self.findChild(QWidget, "selection_actions_widget")
        if widget is not None and widget is not self:
            return widget

        return None

    def _set_selection_actions_visible(self, visible: bool) -> None:
        if self.selection_actions_widget is not None and self.selection_actions_widget is not self:
            self.selection_actions_widget.setVisible(visible)

        self.btn_restore_selected.setVisible(visible)
        self.btn_delete_selected.setVisible(visible)
        self.btn_cancel_selection.setVisible(visible)

    def _format_trash_item_text(self, trash_record: dict) -> str:
        snippet = trash_record.get("snippet") or {}
        title = snippet.get("title") or "שליף ללא שם"
        category = trash_record.get("original_category") or snippet.get("category") or "ללא קטגוריה"
        deleted_at = str(trash_record.get("deleted_at") or "")
        tags = snippet.get("tags") or ""

        lines = [
            str(title),
            f"קטגוריה: {category} | נמחק: {deleted_at}",
        ]
        if tags:
            lines.append(f"תגיות: {tags}")
        return "\n".join(lines)

    def _rebuild_search_index(self) -> None:
        try:
            SnippetSearchEngine().rebuild_index_from_disk()
        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="השחזור הצליח, אבל עדכון אינדקס החיפוש נכשל",
                dev_message=f"עמוד שחזור שליפים: בניית אינדקס החיפוש מחדש אחרי שחזור נכשלה: {str(e)}",
                severity="WARNING",
            )

    def apply_styles(self) -> None:
        self.setStyleSheet("""
            QLabel#lbl_title {
                font-size: 20px;
                font-weight: 700;
            }
            QLabel#lbl_description,
            QLabel#lbl_delete_permanently_hint {
                color: #5f6368;
            }
            QLabel#lbl_trash_items_title {
                font-size: 15px;
                font-weight: 600;
            }
            QGroupBox#wdg_trash_settings {
                border: none;
                background: transparent;
                margin-top: 10px;
                padding: 0;
            }
            QGroupBox#wdg_trash_settings::title {
                subcontrol-origin: margin;
                left: 0;
                padding: 0;
                font-weight: 600;
            }
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #4a505a;
                border-radius: 4px;
                background: #343840;
                color: #e8eaed;
            }
            QPushButton:hover {
                background: #404650;
            }
            QPushButton:disabled {
                color: #8b929c;
                background: #2f333a;
                border-color: #3c414a;
            }
            QPushButton#btn_restore_selected,
            QPushButton#btn_save_trash_settings {
                background: #1a73e8;
                border-color: #1a73e8;
                color: white;
            }
            QPushButton#btn_restore_selected:hover,
            QPushButton#btn_save_trash_settings:hover {
                background: #2b7de9;
            }
            QPushButton#btn_delete_selected {
                background: #4a2c2c;
                color: #ffb4ab;
                border-color: #7d3b35;
            }
            QPushButton#btn_delete_selected:hover {
                background: #5a3332;
            }
            QPushButton#btn_cancel_selection {
                background: #343840;
                color: #e8eaed;
                border-color: #4a505a;
            }
            QFrame#frm_settings_restore_separator {
                color: #3a3f47;
                background: #3a3f47;
                max-height: 1px;
            }
            QListWidget#lst_trash_snippets {
                border: 1px solid #3f444d;
                border-radius: 6px;
                background: #2b2d31;
                color: #e5e7eb;
                outline: none;
            }
            QListWidget#lst_trash_snippets::item {
                padding: 10px;
                border-bottom: 1px solid #3a3f47;
            }
            QListWidget#lst_trash_snippets::item:selected {
                background: #315f9f;
                color: #ffffff;
            }
        """)
