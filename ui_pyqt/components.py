"""Reusable presentation components backed by Qt Designer forms."""

from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QPropertyAnimation
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)

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


class EmptyState(QFrame):
    def __init__(self, icon: str = "", title: str = "", subtitle: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", True)
        layout = __import__("PyQt6.QtWidgets", fromlist=["QVBoxLayout"]).QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon:
            self._icon = QLabel(icon)
            self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._icon.setStyleSheet("font-size: 32px;")
            layout.addWidget(self._icon)
        self._title = QLabel(title)
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setProperty("muted", True)
        layout.addWidget(self._title)
        if subtitle:
            self._subtitle = QLabel(subtitle)
            self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._subtitle.setProperty("muted", True)
            self._subtitle.setWordWrap(True)
            layout.addWidget(self._subtitle)


class Toast(QFrame):
    shown = pyqtSignal()

    def __init__(self, message: str, kind: str = "info", duration_ms: int = 3000, parent: QWidget | None = None):
        super().__init__(parent)
        self.kind = kind
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowFlags(Qt.WindowType.ToolTip)
        layout = __import__("PyQt6.QtWidgets", fromlist=["QHBoxLayout"]).QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)
        icon_map = {"info": "ℹ", "success": "✓", "warning": "⚠", "error": "✕"}
        icon_label = QLabel(icon_map.get(kind, "ℹ"))
        icon_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(icon_label)
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)
        self._label = msg_label
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0)
        QTimer.singleShot(50, lambda: self.show_toast(duration_ms))

    def show_toast(self, duration_ms: int) -> None:
        self.adjustSize()
        pos = self.mapToGlobal(self.rect().center())
        self.move(pos.x() - self.width() // 2, pos.y() - self.height() // 2)
        self.show()
        anim = QPropertyAnimation(self._opacity, b"opacity")
        anim.setDuration(250)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.start()
        self.shown.emit()
        QTimer.singleShot(duration_ms, self._fade_out)

    def _fade_out(self) -> None:
        anim = QPropertyAnimation(self._opacity, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(self.deleteLater)
        anim.start()


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
