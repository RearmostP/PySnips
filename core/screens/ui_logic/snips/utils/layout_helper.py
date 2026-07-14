from PySide6.QtWidgets import QGridLayout, QLayoutItem, QWidget

from core.tools.common.error_manager import AppDebugger


class LayoutHelper:
    @staticmethod
    def replace_widget_in_grid_layout(layout: QGridLayout, old_widget: QWidget, new_widget: QWidget) -> bool:
        if not layout or not old_widget or not new_widget:
            AppDebugger.log("Invalid arguments for replace_widget_in_grid_layout.")
            return False

        row, col, rowspan, colspan = -1, -1, -1, -1
        item_to_remove: QLayoutItem | None = None

        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item and item.widget() == old_widget:
                row, col, rowspan, colspan = layout.getItemPosition(index)
                item_to_remove = item
                break

        if row == -1:
            AppDebugger.log(f"Old widget {old_widget} was not found in layout for replacement.")
            return False

        if item_to_remove:
            layout.removeItem(item_to_remove)
        layout.removeWidget(old_widget)
        old_widget.deleteLater()

        layout.addWidget(new_widget, row, col, rowspan, colspan)
        return True
