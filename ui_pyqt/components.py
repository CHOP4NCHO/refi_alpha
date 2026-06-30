"""Reusable presentation components backed by Qt Designer forms."""

from PyQt6.QtWidgets import QFrame, QWidget

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
