"""Workspace and explicit evaluation-context selection."""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFileDialog,
    QListWidgetItem,
    QMessageBox,
    QTreeWidgetItem,
    QWidget,
)

from .ui_loader import load_ui


class WorkspacePage(QWidget):
    context_changed = pyqtSignal()
    message = pyqtSignal(str)

    def __init__(self, service, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        load_ui("workspace_page.ui", self)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        self.workspace_label.setObjectName("sectionTitle")
        self.change_button.clicked.connect(self.choose_workspace)
        self.path_input.returnPressed.connect(self.add_path)
        self.add_button.clicked.connect(self.add_path)
        self.tree.setColumnWidth(0, 390)
        self.tree.itemDoubleClicked.connect(self.toggle_tree_item)
        self.context_list.itemDoubleClicked.connect(self.remove_context_item)
        self.clear_button.clicked.connect(self.clear_context)
        self.splitter.setSizes([680, 380])

    def refresh(self) -> None:
        codebase = self.service.codebase
        self.workspace_label.setText(codebase.name if codebase else "Sin repositorio")
        self.tree.clear()
        if not codebase:
            self._refresh_context()
            return

        base_path = Path(codebase.path)
        directory_items: dict[tuple[str, ...], QTreeWidgetItem] = {}
        context_paths = {str(Path(file.path)) for file in self.service.file_context}
        for file_obj in sorted(codebase.files, key=lambda item: str(item.path).lower()):
            try:
                relative = Path(file_obj.path).relative_to(base_path)
            except ValueError:
                continue
            parent = self.tree.invisibleRootItem()
            for depth, part in enumerate(relative.parts[:-1], start=1):
                key = relative.parts[:depth]
                if key not in directory_items:
                    directory_items[key] = QTreeWidgetItem(parent, [part, ""])
                parent = directory_items[key]

            file_path = str(Path(file_obj.path))
            selected = file_path in context_paths
            item = QTreeWidgetItem(parent, [relative.name, "Incluido" if selected else "Disponible"])
            item.setData(0, Qt.ItemDataRole.UserRole, file_path)
            self._style_file_item(item, selected)

        self.tree.resizeColumnToContents(1)
        self._refresh_context()

    def _style_file_item(self, item: QTreeWidgetItem, selected: bool) -> None:
        color = QColor("#63e6be" if selected else "#8ea3b8")
        item.setForeground(0, color)
        item.setForeground(1, color)

    def _refresh_context(self) -> None:
        self.context_list.clear()
        codebase = self.service.codebase
        base_path = Path(codebase.path) if codebase else None
        for file_obj in self.service.file_context:
            path = Path(file_obj.path)
            try:
                label = str(path.relative_to(base_path)) if base_path else path.name
            except ValueError:
                label = path.name
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.context_list.addItem(item)
        self.context_changed.emit()

    def choose_workspace(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Selecciona el espacio de trabajo")
        if not directory:
            return
        try:
            self.service.set_workdir(directory, Path(directory).name)
        except Exception as error:
            QMessageBox.critical(self, "No se pudo abrir", str(error))
            return
        self.message.emit(f"Espacio de trabajo cambiado a: {directory}")
        self.refresh()

    def add_path(self) -> None:
        relative_path = self.path_input.text().strip()
        if not relative_path:
            QMessageBox.warning(self, "Ruta requerida", "Ingresa una ruta relativa válida.")
            return
        codebase = self.service.codebase
        if not codebase:
            QMessageBox.warning(self, "Sin repositorio", "Selecciona primero un espacio de trabajo.")
            return
        path = Path(codebase.path) / relative_path
        try:
            if path.is_dir():
                added = self.service.add_directory_to_context(path)
                self.message.emit(f"Directorio añadido al contexto: {relative_path} ({added} archivos nuevos)")
            else:
                added = self.service.add_file_to_context(path)
                self.message.emit(f"Archivo {'añadido' if added else 'ya presente'}: {relative_path}")
        except Exception as error:
            QMessageBox.critical(self, "No se pudo añadir", str(error))
            return
        self.path_input.clear()
        self.refresh()

    def toggle_tree_item(self, item: QTreeWidgetItem, _column: int) -> None:
        path_string = item.data(0, Qt.ItemDataRole.UserRole)
        if not path_string:
            item.setExpanded(not item.isExpanded())
            return
        path = Path(path_string)
        try:
            in_context = any(Path(file.path) == path for file in self.service.file_context)
            if in_context:
                self.service.remove_file_from_context(path)
                self.message.emit(f"Quitado del contexto: {path.name}")
            else:
                self.service.add_file_to_context(path)
                self.message.emit(f"Añadido al contexto: {path.name}")
        except Exception as error:
            QMessageBox.critical(self, "No se pudo actualizar", str(error))
            return
        self.refresh()

    def remove_context_item(self, item: QListWidgetItem) -> None:
        path = Path(item.data(Qt.ItemDataRole.UserRole))
        self.service.remove_file_from_context(path)
        self.message.emit(f"Quitado del contexto: {path.name}")
        self.refresh()

    def clear_context(self) -> None:
        if not self.service.file_context:
            return
        self.service.clear_file_context()
        self.message.emit("Contexto de archivos vaciado.")
        self.refresh()
