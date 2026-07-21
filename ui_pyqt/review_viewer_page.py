"""Read-only viewer for a previously exported evaluation JSON."""

from html import escape

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QDialog,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .ui_loader import load_ui


class ReviewViewerPage(QWidget):
    """Displays a loaded ReqFidelityReview JSON as a read-only table."""

    back_requested = pyqtSignal()

    def __init__(self, review_data: dict, theme_manager=None, parent=None):
        super().__init__(parent)
        self.review_data = review_data
        self.theme_manager = theme_manager
        load_ui("review_viewer_page.ui", self)
        self._setup_ui()
        self._populate_table()

    def _setup_ui(self) -> None:
        self.btn_export.clicked.connect(self._export_json)
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.metaInfo.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.reqsTable.setAlternatingRowColors(True)
        self.reqsTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.reqsTable.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.reqsTable.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.reqsTable.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.reqsTable.setColumnWidth(0, 40)
        self.reqsTable.setColumnWidth(2, 100)
        self.reqsTable.verticalHeader().setVisible(False)
        self.reqsTable.cellDoubleClicked.connect(self._show_requirement_detail)
        self._populate_meta()

    def _populate_meta(self) -> None:
        meta = self.review_data
        token_usage = meta.get("token_usage", {})
        input_tokens = meta.get("input_tokens", token_usage.get("input", 0))
        output_tokens = meta.get("output_tokens", token_usage.get("output", 0))
        try:
            response_time = float(meta.get("response_time", 0))
        except (TypeError, ValueError):
            response_time = 0.0

        lines = [
            f"<b>Fecha:</b> {escape(str(meta.get('review_date', '-'))) }",
            f"<b>Proveedor LLM:</b> {escape(str(meta.get('llm_provider', '-'))) }",
            f"<b>Modo evaluacion:</b> {escape(str(meta.get('evaluation_mode', '-'))) }",
            f"<b>Evaluacion real:</b> {escape(str(meta.get('real_evaluation', '-'))) }",
            f"<b>Tokens entrada:</b> {input_tokens}  |  "
            f"<b>Tokens salida:</b> {output_tokens}  |  "
            f"<b>Tiempo:</b> {response_time:.2f}s",
        ]
        if meta.get("debug_mode"):
            lines.append("<b>Modo debug:</b> activo")
        self.metaInfo.setText(" &nbsp;·&nbsp; ".join(lines))

    def _reviewed_requirements(self) -> list[dict]:
        reqs = self.review_data.get("reviewed_reqs")
        if reqs is None:
            reqs = self.review_data.get("requirements", [])
        return reqs if isinstance(reqs, list) else []

    def _requirement_description(self, req: dict) -> str:
        return req.get("initial_description", req.get("description", ""))

    def _populate_table(self) -> None:
        if self.theme_manager:
            cumple_color = "#16a34a" if not self.theme_manager.is_dark else "#4ade80"
            no_cumple_color = "#dc2626" if not self.theme_manager.is_dark else "#f87171"
        else:
            cumple_color, no_cumple_color = "#16a34a", "#dc2626"
        reqs = self._reviewed_requirements()
        self.reqsTable.setRowCount(len(reqs))
        for i, req in enumerate(reqs):
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.reqsTable.setItem(i, 0, num_item)
            self.reqsTable.setItem(i, 1, QTableWidgetItem(self._requirement_description(req)))
            fulfilled = req.get("is_fulfilled", False)
            result_item = QTableWidgetItem("Cumple" if fulfilled else "No cumple")
            result_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if fulfilled:
                result_item.setForeground(QColor(cumple_color))
            else:
                result_item.setForeground(QColor(no_cumple_color))
            bold_font = QFont("", -1, QFont.Weight.Bold)
            result_item.setFont(bold_font)
            self.reqsTable.setItem(i, 2, result_item)
            self.reqsTable.setItem(i, 3, QTableWidgetItem(req.get("reasoning", "")))

    def _show_requirement_detail(self, row: int, _column: int) -> None:
        reqs = self._reviewed_requirements()
        if row < 0 or row >= len(reqs):
            return
        req = reqs[row]
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Requerimiento #{row + 1}")
        dialog.resize(600, 420)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 18, 20, 18)
        desc_label = QLabel("Requerimiento")
        desc_label.setFont(QFont("", -1, QFont.Weight.Bold))
        layout.addWidget(desc_label)
        desc_text = QLabel(self._requirement_description(req))
        desc_text.setWordWrap(True)
        desc_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(desc_text)
        fulfilled = req.get("is_fulfilled", False)
        result_label = QLabel("Resultado")
        result_label.setFont(QFont("", -1, QFont.Weight.Bold))
        layout.addWidget(result_label)
        result_text = QLabel("Cumple" if fulfilled else "No cumple")
        result_text.setFont(QFont("", -1, QFont.Weight.Bold))
        if self.theme_manager:
            color = "#16a34a" if not self.theme_manager.is_dark else "#4ade80"
            if not fulfilled:
                color = "#dc2626" if not self.theme_manager.is_dark else "#f87171"
        else:
            color = "#16a34a" if fulfilled else "#dc2626"
        result_text.setStyleSheet(f"color: {color};")
        layout.addWidget(result_text)
        reasoning_label = QLabel("Razonamiento")
        reasoning_label.setFont(QFont("", -1, QFont.Weight.Bold))
        layout.addWidget(reasoning_label)
        reasoning_text = QLabel(req.get("reasoning", ""))
        reasoning_text.setWordWrap(True)
        reasoning_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(reasoning_text)
        layout.addStretch()
        if self.theme_manager:
            self.theme_manager.apply_to(dialog)
        dialog.exec()

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
