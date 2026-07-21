"""Theme manager to load, save, toggle and apply light and dark stylesheets with customizations."""

import json
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QWidget

from .theme import LIGHT_STYLESHEET, DARK_STYLESHEET


class ThemeManager(QObject):
    _USER_DIR = Path("~/.refi").expanduser()
    _CONFIG_FILE = _USER_DIR / "config.json"
    _CUSTOM_QSS_FILE = _USER_DIR / "style.qss"

    theme_changed = pyqtSignal()

    LIGHT_COLORS = {
        "text": "#243447",
        "text_muted": "#6f8093",
        "background": "#f4f7fb",
        "surface": "#ffffff",
        "border": "#dce4ee",
        "accent": "#16a34a",
        "accent_hover": "#15803d",
        "warning_bg": "#fff4c2",
        "warning_text": "#765a00",
        "info_bg": "#f5f8fb",
        "info_text": "#294057",
    }

    DARK_COLORS = {
        "text": "#dbe7f4",
        "text_muted": "#7f93aa",
        "background": "#08111f",
        "surface": "#0f1c2e",
        "border": "#20324a",
        "accent": "#63e6be",
        "accent_hover": "#7cebc9",
        "warning_bg": "#422006",
        "warning_text": "#fbbf24",
        "info_bg": "#1e293b",
        "info_text": "#e2e8f0",
    }

    def __init__(self):
        super().__init__()
        self._mode = "light"
        self._custom_qss = ""
        self._load()
        self._load_font()

    def _load_font(self) -> None:
        from pathlib import Path
        from PyQt6.QtGui import QFontDatabase
        font_dir = Path(__file__).parent / "fonts"
        for font_file in sorted(font_dir.glob("rubik-*.ttf")):
            QFontDatabase.addApplicationFont(str(font_file))

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_dark(self) -> bool:
        return self._mode == "dark"

    @property
    def t(self) -> dict:
        """Tokens activos para acceso rápido."""
        return self.DARK_COLORS if self._mode == "dark" else self.LIGHT_COLORS

    def toggle(self) -> str:
        self._mode = "dark" if self._mode == "light" else "light"
        self._save()
        return self._mode

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self._save()

    def apply_to(self, widget: QWidget) -> None:
        base = DARK_STYLESHEET if self._mode == "dark" else LIGHT_STYLESHEET
        final = base + "\n" + self._custom_qss
        widget.setStyleSheet(final)

    def apply_theme(self) -> None:
        """Apply the current theme globally to QApplication (propagates to all windows)."""
        base = DARK_STYLESHEET if self._mode == "dark" else LIGHT_STYLESHEET
        final = base + "\n" + self._custom_qss
        QApplication.instance().setStyleSheet(final)
        self.theme_changed.emit()

    def get_palette_color(self, token: str) -> str:
        palette = self.DARK_COLORS if self._mode == "dark" else self.LIGHT_COLORS
        return palette.get(token, "#ff00ff")

    def reload_custom_qss(self) -> None:
        if self._CUSTOM_QSS_FILE.exists():
            self._custom_qss = self._CUSTOM_QSS_FILE.read_text(encoding="utf-8")
        else:
            self._custom_qss = ""

    def _load(self) -> None:
        self._USER_DIR.mkdir(parents=True, exist_ok=True)
        if self._CONFIG_FILE.exists():
            try:
                data = json.loads(self._CONFIG_FILE.read_text(encoding="utf-8"))
                self._mode = data.get("mode", "light")
            except Exception:
                self._mode = "light"
        self.reload_custom_qss()

    def _save(self) -> None:
        self._USER_DIR.mkdir(parents=True, exist_ok=True)
        self._CONFIG_FILE.write_text(json.dumps({"mode": self._mode}, indent=2), encoding="utf-8")

    def show_message_box(
        self,
        parent: QWidget,
        icon_type: str,
        title: str,
        text: str,
        buttons=None,
    ):
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(parent)
        msg.setWindowTitle(title)
        msg.setText(text)

        if icon_type == "info":
            msg.setIcon(QMessageBox.Icon.Information)
        elif icon_type == "warning":
            msg.setIcon(QMessageBox.Icon.Warning)
        elif icon_type == "critical":
            msg.setIcon(QMessageBox.Icon.Critical)
        elif icon_type == "question":
            msg.setIcon(QMessageBox.Icon.Question)

        if buttons is not None:
            msg.setStandardButtons(buttons)
        elif icon_type == "question":
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        else:
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)

        self.apply_to(msg)
        return msg.exec()
