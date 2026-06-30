"""Requirement import and manual-entry page."""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QTableWidgetItem,
    QWidget,
)

from .ui_loader import load_ui


class RequirementsPage(QWidget):
    import_requested = pyqtSignal(object)
    requirements_changed = pyqtSignal()
    message = pyqtSignal(str)

    def __init__(self, service, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        load_ui("requirements_page.ui", self)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        self.import_button.clicked.connect(self.choose_pdf)
        self.description_input.returnPressed.connect(self.add_requirement)
        self.add_button.clicked.connect(self.add_requirement)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

    def choose_pdf(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Documento de requerimientos", "", "Documentos PDF (*.pdf)")
        if not filename:
            return
        if self.service.get_requirements():
            answer = QMessageBox.question(
                self,
                "Reemplazar requerimientos",
                "La extracción reemplazará los requerimientos actuales. ¿Continuar?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        path = Path(filename)
        self.import_status.setText(f"Extrayendo {path.name}…")
        self.import_button.setEnabled(False)
        self.import_requested.emit(path)

    def finish_import(self, document=None, error: str | None = None) -> None:
        self.import_button.setEnabled(True)
        if error:
            self.import_status.setText("No fue posible completar la extracción")
            return
        count = len(document.requirements)
        self.import_status.setText(f"{document.name} · {count} requerimiento(s)")
        self.refresh()

    def add_requirement(self) -> None:
        description = self.description_input.text().strip()
        if not description:
            QMessageBox.warning(self, "Descripción requerida", "La descripción no puede estar vacía.")
            return
        requirement_type = "FUNCTIONAL" if self.functional_radio.isChecked() else "NON_FUNCTIONAL"
        try:
            requirement = self.service.add_requirement(description, requirement_type)
        except Exception as error:
            QMessageBox.critical(self, "No se pudo agregar", str(error))
            return
        self.description_input.clear()
        self.message.emit(f"Requerimiento agregado: [{requirement.id}] {description}")
        self.refresh()

    def refresh(self) -> None:
        requirements = self.service.get_requirements()
        self.table.setRowCount(len(requirements))
        for row, requirement in enumerate(requirements):
            values = (requirement.id, str(requirement.type), requirement.description)
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column < 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, item)
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)
        self.requirements_changed.emit()
