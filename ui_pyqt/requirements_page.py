"""Requirement import and manual-entry page."""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QFileDialog,
    QHeaderView,
    QMessageBox,
    QPushButton,
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
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(3, 90)
        self.table.verticalHeader().setVisible(False)

    def set_compact(self, compact: bool) -> None:
        direction = (
            QBoxLayout.Direction.TopToBottom
            if compact
            else QBoxLayout.Direction.LeftToRight
        )
        self.entryRow.setDirection(direction)
        self.importRow.setDirection(direction)

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
            requirement = self.service.add_requirement(
                description, requirement_type, self.id_input.text().strip() or None
            )
        except Exception as error:
            QMessageBox.critical(self, "No se pudo agregar", str(error))
            return
        self.description_input.clear()
        self.id_input.clear()
        self.message.emit(f"Requerimiento agregado: [{requirement.id}] {description}")
        self.refresh()

    def refresh(self) -> None:
        requirements = self.service.get_requirements()
        self.table.setRowCount(len(requirements))
        for row, requirement in enumerate(requirements):
            values = (requirement.id, requirement.description)
            for column, value in ((0, values[0]), (2, values[1])):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, item)
            type_combo = QComboBox(self.table)
            type_combo.addItem("Funcional", "FUNCTIONAL")
            type_combo.addItem("No Funcional", "NON_FUNCTIONAL")
            type_combo.setCurrentIndex(0 if requirement.type == "FUNCTIONAL" else 1)
            type_combo.currentIndexChanged.connect(
                lambda _index, req_id=requirement.id, combo=type_combo: self.change_type(req_id, combo)
            )
            self.table.setCellWidget(row, 1, type_combo)
            delete_button = QPushButton("Eliminar", self.table)
            delete_button.clicked.connect(
                lambda _checked=False, req_id=requirement.id: self.delete_requirement(req_id)
            )
            self.table.setCellWidget(row, 3, delete_button)
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)
        self.requirements_changed.emit()

    def change_type(self, requirement_id: str, combo: QComboBox) -> None:
        try:
            self.service.update_requirement_type(requirement_id, combo.currentData())
        except Exception as error:
            QMessageBox.critical(self, "No se pudo actualizar", str(error))
            self.refresh()
            return
        self.message.emit(f"Tipo actualizado para el requerimiento [{requirement_id}].")
        self.requirements_changed.emit()

    def delete_requirement(self, requirement_id: str) -> None:
        answer = QMessageBox.question(
            self, "Eliminar requerimiento", f"¿Eliminar el requerimiento [{requirement_id}]?"
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.service.remove_requirement(requirement_id):
            self.message.emit(f"Requerimiento eliminado: [{requirement_id}]")
            self.refresh()
