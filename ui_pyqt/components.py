"""Reusable presentation components backed by Qt Designer forms."""

from PyQt6.QtWidgets import QFrame, QWidget, QComboBox, QMessageBox

from .ui_loader import load_ui


class Metric(QFrame):
    def __init__(self, label: str, value: str = "0", parent: QWidget | None = None):
        super().__init__(parent)
        load_ui("metric.ui", self)
        self.caption_label.setText(label)
        self.value_label.setText(value)
        self.value_label.setObjectName("metricValue")

    def set_value(self, value: str | int) -> None:
        self.value_label.setText(str(value))


def populate_combo(combo: QComboBox, items: list[tuple[str, any]], current=None) -> None:
    combo.blockSignals(True)
    combo.clear()
    for label, data in items:
        combo.addItem(label, data)
    if current is not None:
        for index in range(combo.count()):
            if combo.itemData(index) == current:
                combo.setCurrentIndex(index)
                break
    combo.blockSignals(False)


def safe_operation(parent: QWidget, fn, error_title: str = "Error"):
    try:
        return fn()
    except Exception as error:
        if hasattr(parent, "_show_messagebox"):
            parent._show_messagebox("critical", error_title, str(error))
        else:
            QMessageBox.critical(parent, error_title, str(error))
        return None
