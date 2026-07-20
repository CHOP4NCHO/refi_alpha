"""Read-only viewer for a previously exported evaluation JSON."""

from html import escape

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ReviewViewerPage(QWidget):
    """Displays a loaded ReqFidelityReview JSON as a read-only table."""

    back_requested = pyqtSignal()

    def __init__(self, review_data: dict, theme_manager=None, parent=None):
        super().__init__(parent)
        self.review_data = review_data
        self.theme_manager = theme_manager
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)

        btn_back = QPushButton("← Volver a inicio")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.back_requested.emit)
        header.addWidget(btn_back)

        header.addStretch()

        btn_export = QPushButton("Exportar JSON")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.clicked.connect(self._export_json)
        header.addWidget(btn_export)

        root.addLayout(header)

        meta_card = QFrame()
        meta_card.setProperty("card", True)
        meta_layout = QVBoxLayout(meta_card)
        meta_layout.setContentsMargins(16, 14, 16, 14)
        meta_layout.setSpacing(6)

        meta_title = QLabel("Metadata de la evaluacion")
        meta_title.setObjectName("sectionTitle")
        meta_layout.addWidget(meta_title)

        meta = self.review_data
        lines = [
            f"<b>Fecha:</b> {escape(str(meta.get('review_date', '-')))}",
            f"<b>Proveedor LLM:</b> {escape(str(meta.get('llm_provider', '-')))}",
            f"<b>Modo evaluacion:</b> {escape(str(meta.get('evaluation_mode', '-')))}",
            f"<b>Evaluacion real:</b> {escape(str(meta.get('real_evaluation', '-')))}",
            f"<b>Tokens entrada:</b> {meta.get('input_tokens', 0)}  |  "
            f"<b>Tokens salida:</b> {meta.get('output_tokens', 0)}  |  "
            f"<b>Tiempo:</b> {meta.get('response_time', 0):.2f}s",
        ]
        if meta.get("debug_mode"):
            lines.append("<b>Modo debug:</b> activo")

        info = QLabel(" &nbsp;·&nbsp; ".join(lines))
        info.setWordWrap(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        meta_layout.addWidget(info)

        root.addWidget(meta_card)

        reqs_title = QLabel("Requerimientos evaluados")
        reqs_title.setObjectName("sectionTitle")
        root.addWidget(reqs_title)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["#", "Requerimiento", "Resultado", "Razonamiento"])
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(0, 40)
        table.setColumnWidth(2, 100)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        reqs = self.review_data.get("reviewed_reqs", [])
        table.setRowCount(len(reqs))
        for i, req in enumerate(reqs):
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 0, num_item)

            table.setItem(i, 1, QTableWidgetItem(req.get("initial_description", "")))

            fulfilled = req.get("is_fulfilled", False)
            result_item = QTableWidgetItem("Cumple" if fulfilled else "No cumple")
            result_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 2, result_item)

            table.setItem(i, 3, QTableWidgetItem(req.get("reasoning", "")))

        table.verticalHeader().setVisible(False)
        root.addWidget(table)

    def _export_json(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path
        import json
        from enum import Enum

        date_str = self.review_data.get("review_date", "review")
        safe_name = date_str.replace(" ", "_").replace(":", "-")
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar informe de fidelidad",
            f"review_{safe_name}.json",
            "JSON Files (*.json)",
        )
        if not filename:
            return

        def _serializer(obj):
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(f"Type {type(obj)} not serializable")

        try:
            json_data = json.dumps(
                self.review_data, indent=2, ensure_ascii=False, default=_serializer
            )
            Path(filename).write_text(json_data, encoding="utf-8")
            if self.theme_manager:
                self.theme_manager.show_message_box(
                    self, "info", "Exportacion exitosa",
                    f"Informe exportado a:\n{filename}",
                )
        except Exception as error:
            if self.theme_manager:
                self.theme_manager.show_message_box(
                    self, "critical", "Error al exportar", str(error)
                )
