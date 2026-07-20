"""Landing page with three main entry points for the application."""

import json
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
)


class LandingPage(QWidget):
    """Initial screen offering three options: new evaluation, review saved, about."""

    new_evaluation_requested = pyqtSignal()
    review_loaded = pyqtSignal(object)

    def __init__(self, theme_manager=None, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setProperty("card", True)
        card.setFixedWidth(600)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(40, 44, 40, 44)

        logo_label = QLabel()
        logo_path = Path(__file__).with_name("refi.png")
        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            logo_label.setPixmap(
                pixmap.scaled(
                    96, 96,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setMinimumHeight(96)
        card_layout.addWidget(logo_label)

        title = QLabel("REFI ALPHA")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("Herramienta de Revisión y Evaluación de Proyectos\nde Software basado en Agentes IA")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setProperty("muted", True)
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(28)

        btn_new = QPushButton("Realizar Nueva evaluacion")
        btn_new.setProperty("landing", True)
        btn_new.setProperty("primary", True)
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.clicked.connect(self.new_evaluation_requested.emit)
        card_layout.addWidget(btn_new)

        btn_review = QPushButton("Revisar evaluacion guardada")
        btn_review.setProperty("landing", True)
        btn_review.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_review.clicked.connect(self._on_review_clicked)
        card_layout.addWidget(btn_review)

        btn_about = QPushButton("Acerca de")
        btn_about.setProperty("landing", True)
        btn_about.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_about.clicked.connect(self._on_about_clicked)
        card_layout.addWidget(btn_about)

        outer.addWidget(card)

    def _on_review_clicked(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar informe de evaluacion",
            "",
            "Archivos JSON (*.json);;Todos los archivos (*)",
        )
        if not filename:
            return
        try:
            raw = Path(filename).read_text(encoding="utf-8")
            data = json.loads(raw)
            self._validate_review_json(data)
            self.review_loaded.emit(data)
        except json.JSONDecodeError:
            QMessageBox.critical(
                self,
                "Archivo invalido",
                "El archivo seleccionado no es un JSON valido.",
            )
        except KeyError as e:
            QMessageBox.critical(
                self,
                "Formato incompleto",
                f"El JSON no contiene el campo esperado: {e}",
            )

    def _validate_review_json(self, data: dict) -> None:
        required = ["review_date", "reviewed_reqs", "llm_provider"]
        for key in required:
            if key not in data:
                raise KeyError(key)
        for req in data["reviewed_reqs"]:
            for field in ("initial_description", "reasoning", "is_fulfilled"):
                if field not in req:
                    raise KeyError(f"reviewed_reqs[].{field}")

    def _on_about_clicked(self) -> None:
        QMessageBox.information(
            self,
            "Acerca de REFI ALPHA",
            "REFI ALPHA - Requirements Fidelity\n\n"
            "Herramienta de evaluacion automatizada de requisitos "
            "utilizando inteligencia artificial.\n\n"
            "Espacio reservado para informacion del proyecto.",
        )
