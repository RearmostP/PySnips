from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget

from core.tools.common.app_paths import AppPaths
from core.tools.common.dynamic_ui_loader import create_dynamic_ui_loader
from core.tools.common.error_manager import AppDebugger, AppErrorHandler
from core.tools.snips.snippet_content_store import SnippetContentStore


class EditCardWidget(create_dynamic_ui_loader(AppPaths.EDIT_CARD_WIDGET)):
    """UI adapter for editing the Markdown source of an existing snippet."""

    def __init__(
        self,
        snippet_meta: dict,
        on_save_callback,
        on_cancel_callback,
        parent: QWidget | None = None,
        content_store: SnippetContentStore | None = None,
    ):
        super().__init__(parent)
        self.snippet_meta = snippet_meta
        self.on_save_callback = on_save_callback
        self.on_cancel_callback = on_cancel_callback
        self.content_store = content_store or SnippetContentStore()

        self.init_data()
        self.setup_logic()

    def init_data(self) -> None:
        AppDebugger.log(
            f"EditCardWidget: טוען תוכן עבור שליף ID: {self.snippet_meta.get('id')}"
        )
        content_file_path = Path(str(self.snippet_meta.get("content_file") or ""))
        try:
            content = self.content_store.read(content_file_path)
        except FileNotFoundError:
            AppDebugger.log(
                f"EditCardWidget: קובץ תוכן לא נמצא עבור שליף ID: {self.snippet_meta.get('id')}"
            )
            QMessageBox.warning(self, "שגיאה", "קובץ תוכן השליף לא נמצא.")
            return
        except Exception as error:
            AppErrorHandler.handle_error(
                error_obj=error,
                user_message="שגיאה בטעינת תוכן השליף לעריכה.",
                dev_message=f"EditCardWidget: טעינת תוכן השליף נכשלה: {error}",
                severity="ERROR",
            )
            return

        self.txt_snippet_content.setPlainText(content)

    def setup_logic(self) -> None:
        AppDebugger.log("EditCardWidget: מחבר אירועים ורכיבי ממשק...")
        self.btn_save_edit.clicked.connect(self._save_snippet)
        self.btn_cancel_edit.clicked.connect(self._cancel_edit)

    def _save_snippet(self) -> None:
        AppDebugger.log(
            f"EditCardWidget: שומר שליף ID: {self.snippet_meta.get('id')}"
        )
        content_file_path = Path(str(self.snippet_meta.get("content_file") or ""))
        try:
            self.content_store.write(
                content_file_path,
                self.txt_snippet_content.toPlainText(),
            )
        except Exception as error:
            AppErrorHandler.handle_error(
                error_obj=error,
                user_message="נכשלה שמירת השליף.",
                dev_message=f"EditCardWidget: שמירת תוכן השליף נכשלה: {error}",
                severity="ERROR",
            )
            return

        self.on_save_callback(self.snippet_meta)

    def _cancel_edit(self) -> None:
        AppDebugger.log("EditCardWidget: מבטל עריכת שליף.")
        self.on_cancel_callback()

    def get_view(self) -> QWidget:
        return self
