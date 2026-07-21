"""Workspace and explicit evaluation-context selection."""

from pathlib import Path

from PyQt6.QtCore import QEvent, QMimeData, QPoint, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QStyle,
    QTreeWidgetItem,
    QWidget,
)

from .ui_loader import load_ui


class WorkspacePage(QWidget):
    context_changed = pyqtSignal()
    message = pyqtSignal(str)

    def __init__(self, service, parent: QWidget | None = None, theme_manager=None):
        super().__init__(parent)
        self.service = service
        self.theme_manager = theme_manager
        self._drag_start = QPoint()
        self._drag_hover = False
        load_ui("workspace_page.ui", self)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        route_font = QFont()
        route_font.setPointSize(10)
        self.workspace_label.setObjectName("sectionTitle")
        self.workspace_path_label = QLabel(self.workspaceCard)
        self.workspace_path_label.setObjectName("workspacePathLabel")
        self.workspace_path_label.setProperty("muted", True)
        self.workspace_path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.workspace_path_label.setFont(route_font)
        self.workspace_path_label.setWordWrap(True)
        self.workspaceCardLayout.insertWidget(3, self.workspace_path_label)
        self.change_button.clicked.connect(self.choose_workspace)
        self.path_input.returnPressed.connect(self.add_path)
        self.add_button.clicked.connect(self.add_path)
        self.tree.setColumnWidth(0, 390)
        self.tree.setDragEnabled(True)
        self.tree.viewport().installEventFilter(self)
        self.context_list.setAcceptDrops(True)
        self.context_list.viewport().setAcceptDrops(True)
        self.context_list.installEventFilter(self)
        self.context_list.viewport().installEventFilter(self)
        self.tree.itemDoubleClicked.connect(self.toggle_tree_item)
        self.context_list.itemDoubleClicked.connect(self.remove_context_item)
        self.clear_button.clicked.connect(self.clear_context)

        from PyQt6.QtWidgets import QLineEdit
        self.filter_input = QLineEdit(self)
        self.filter_input.setPlaceholderText("Filtrar archivos...")
        self.filter_input.textChanged.connect(self._filter_tree)
        idx = self.treeCardLayout.indexOf(self.tree)
        self.treeCardLayout.insertWidget(idx, self.filter_input)
        self.splitter.setSizes([680, 380])

        self._empty_indicator = QLabel("Arrastra archivos aquí o haz doble clic en el árbol para añadirlos.", self.contextCard)
        self._empty_indicator.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._empty_indicator.setProperty("muted", True)
        self._empty_indicator.setWordWrap(True)
        self._empty_indicator.setMinimumHeight(60)
        self.contextCardLayout.insertWidget(3, self._empty_indicator)
        self.gridLayout.setRowStretch(0, 0)
        self.gridLayout.setRowStretch(1, 1)

    def set_compact(self, compact: bool) -> None:
        orientation = Qt.Orientation.Vertical if compact else Qt.Orientation.Horizontal
        if self.splitter.orientation() == orientation:
            return
        self.splitter.setOrientation(orientation)
        self.splitter.setSizes([360, 260] if compact else [680, 380])

    def refresh(self) -> None:
        codebase = self.service.codebase
        self.workspace_label.setText(codebase.name if codebase else "Sin repositorio")
        self.workspace_path_label.setText(
            f"Ruta: {Path(codebase.path).resolve()}" if codebase else "Ruta: —"
        )
        self.tree.clear()
        if not codebase:
            self._refresh_context()
            return

        base_path = Path(codebase.path)
        directory_items: dict[tuple[str, ...], QTreeWidgetItem] = {}
        context_paths = {str(Path(file.path)) for file in self.service.file_context}
        for file_obj in sorted(codebase.files, key=lambda item: str(item.path).lower(), reverse=True):
            try:
                relative = Path(file_obj.path).relative_to(base_path)
            except ValueError:
                continue
            parent = self.tree.invisibleRootItem()
            for depth, part in enumerate(relative.parts[:-1], start=1):
                key = relative.parts[:depth]
                if key not in directory_items:
                    directory_items[key] = QTreeWidgetItem(parent, [part])
                    directory_items[key].setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
                    text_color = self.theme_manager.get_palette_color("text") if self.theme_manager else "#26384a"
                    directory_items[key].setForeground(0, QColor(text_color))
                parent = directory_items[key]

            file_path = str(Path(file_obj.path))
            selected = file_path in context_paths
            item = QTreeWidgetItem(parent, [relative.name])
            item.setData(0, Qt.ItemDataRole.UserRole, file_path)
            item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
            self._style_file_item(item, selected)
        self._sort_tree(self.tree.invisibleRootItem())
        self._refresh_context()

    def _style_file_item(self, item: QTreeWidgetItem, selected: bool) -> None:
        text_color = self.theme_manager.get_palette_color("text") if self.theme_manager else "#26384a"
        item.setForeground(0, QColor(text_color))
        font = item.font(0)
        font.setBold(selected)
        item.setFont(0, font)
        item.setToolTip(0, "Incluido en el contexto" if selected else "Disponible")

    def _sort_tree(self, parent: QTreeWidgetItem) -> None:
        children = [parent.takeChild(0) for _ in range(parent.childCount())]
        children.sort(
            key=lambda child: (
                1 if child.data(0, Qt.ItemDataRole.UserRole) is None else 0,
                child.text(0).casefold(),
            ),
            reverse=False,
        )
        for child in children:
            parent.addChild(child)
            self._sort_tree(child)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.tree.viewport():
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_start = event.position().toPoint()
            elif event.type() == QEvent.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton:
                if (event.position().toPoint() - self._drag_start).manhattanLength() >= QApplication.startDragDistance():
                    item = self.tree.itemAt(self._drag_start)
                    path_string = item.data(0, Qt.ItemDataRole.UserRole) if item else None
                    if path_string:
                        mime = QMimeData()
                        mime.setUrls([QUrl.fromLocalFile(path_string)])
                        drag = QDrag(self.tree)
                        drag.setMimeData(mime)
                        drag.exec(Qt.DropAction.CopyAction)
                        return True
        if watched in (self.context_list, self.context_list.viewport()):
            if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                if self._contains_only_files(event.mimeData()):
                    event.acceptProposedAction()
                    if not self._drag_hover:
                        self._drag_hover = True
                        self._update_drop_appearance(True)
                    return True
                event.ignore()
                self._drag_hover = False
                self._update_drop_appearance(False)
                return True
            elif event.type() == QEvent.Type.DragLeave:
                self._drag_hover = False
                self._update_drop_appearance(False)
                return True
            elif event.type() == QEvent.Type.Drop and event.mimeData().hasUrls():
                self._drag_hover = False
                self._update_drop_appearance(False)
                paths = [Path(url.toLocalFile()) for url in event.mimeData().urls()]
                if paths and all(path.is_file() for path in paths):
                    self._add_dropped_files(paths)
                    event.acceptProposedAction()
                else:
                    event.ignore()
                    self.message.emit("Arrastre rechazado: sólo se permiten archivos, no directorios.")
                return True
        return super().eventFilter(watched, event)

    @staticmethod
    def _contains_only_files(mime_data: QMimeData) -> bool:
        if not mime_data.hasUrls():
            return False
        paths = [Path(url.toLocalFile()) for url in mime_data.urls()]
        return bool(paths) and all(path.is_file() for path in paths)

    def _add_dropped_files(self, paths: list[Path]) -> None:
        paths = [path for path in paths if path.is_file()]
        if not paths:
            return
        added = 0
        try:
            for path in paths:
                added += int(self.service.add_file_to_context(path))
        except Exception as error:
            self._show_messagebox("critical", "No se pudo añadir", str(error))
            return
        self.message.emit(f"{added} archivo(s) arrastrado(s) al contexto.")
        self.refresh()

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
        self._update_empty_context_indicator()
        self.context_changed.emit()

    def _update_empty_context_indicator(self) -> None:
        if hasattr(self, "_empty_indicator"):
            self._empty_indicator.setVisible(not self.service.file_context)
            self.context_list.setAcceptDrops(not bool(self.service.file_context))

    def _update_drop_appearance(self, hovering: bool) -> None:
        if self.theme_manager:
            accent = self.theme_manager.get_palette_color("accent")
            surface = self.theme_manager.get_palette_color("surface")
            text_muted = self.theme_manager.get_palette_color("text_muted")
        else:
            accent = "#16a34a"
            surface = "#ffffff"
            text_muted = "#6f8093"
        if hovering:
            self.context_list.viewport().setStyleSheet(
                f"QListWidget {{ border: 2px dashed {accent}; background: {surface}; }}"
                f'QLabel {{ color: {text_muted}; }}'
            )
        else:
            self.context_list.viewport().setStyleSheet("")

    def choose_workspace(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Selecciona el espacio de trabajo")
        if not directory:
            return
        if self.service.file_context or self.service.get_requirements():
            from PyQt6.QtWidgets import QMessageBox
            answer = self._show_messagebox(
                "question",
                "Cambiar espacio de trabajo",
                "Se perderán el contexto y los requerimientos actuales. ¿Continuar?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            self.service.set_workdir(directory, Path(directory).name)
        except Exception as error:
            self._show_messagebox("critical", "No se pudo abrir", str(error))
            return
        self.message.emit(f"Espacio de trabajo cambiado a: {directory}")
        self.refresh()

    def add_path(self) -> None:
        relative_path = self.path_input.text().strip()
        if not relative_path:
            self._show_messagebox("warning", "Ruta requerida", "Ingresa una ruta relativa válida.")
            return
        codebase = self.service.codebase
        if not codebase:
            self._show_messagebox("warning", "Sin repositorio", "Selecciona primero un espacio de trabajo.")
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
            self._show_messagebox("critical", "No se pudo añadir", str(error))
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
            self._show_messagebox("critical", "No se pudo actualizar", str(error))
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

    def _filter_tree(self, text: str) -> None:
        from PyQt6.QtWidgets import QTreeWidgetItemIterator
        text = text.lower()
        if not text:
            iterator = QTreeWidgetItemIterator(self.tree)
            while iterator.value():
                iterator.value().setHidden(False)
                iterator += 1
            return

        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            iterator.value().setHidden(True)
            iterator += 1

        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            item_text = item.text(0).lower()
            if text in item_text:
                curr = item
                while curr:
                    curr.setHidden(False)
                    curr = curr.parent()
            iterator += 1

    def _show_messagebox(self, icon_type: str, title: str, text: str, buttons=None):
        if self.theme_manager:
            return self.theme_manager.show_message_box(self, icon_type, title, text, buttons)
    
        if icon_type == "info":
            return QMessageBox.information(self, title, text)
        elif icon_type == "warning":
            return QMessageBox.warning(self, title, text)
        elif icon_type == "critical":
            return QMessageBox.critical(self, title, text)
        elif icon_type == "question":
            return QMessageBox.question(self, title, text)

    def _populate_combo(self, combo, items, current=None):
        from .components import populate_combo
        populate_combo(combo, items, current)

    def _safe_operation(self, fn, error_title="Error"):
        from .components import safe_operation
        return safe_operation(self, fn, error_title)
