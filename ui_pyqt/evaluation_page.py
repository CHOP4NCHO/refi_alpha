"""Evaluation controls and historical result viewer."""

from html import escape

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QBoxLayout,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from core.enums import EvaluationMode

from .components import Metric
from .ui_loader import load_ui


class EvaluationPage(QWidget):
    evaluation_requested = pyqtSignal()

    def __init__(self, service, parent: QWidget | None = None, theme_manager=None):
        super().__init__(parent)
        self.service = service
        self.theme_manager = theme_manager
        load_ui("evaluation_page.ui", self)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        self.run_button.clicked.connect(self.evaluation_requested)
        self.review_combo.currentIndexChanged.connect(self.show_selected_review)
        self.refresh_button.clicked.connect(self.refresh)
        self.export_button = QPushButton("Exportar", self.resultsCard)
        self.export_button.clicked.connect(self.export_selected_review)
        self.resultRow.addWidget(self.export_button)
        self.state_label.setText("Lista para comenzar")
        self.summary_layout = QHBoxLayout()
        self.files_metric = Metric("Archivos", "0")
        self.requirements_metric = Metric("Requisitos", "0")
        self.reviews_metric = Metric("Informe", "0")
        for metric in (self.files_metric, self.requirements_metric, self.reviews_metric):
            self.summary_layout.addWidget(metric)
        self.actionCardLayout.insertLayout(2, self.summary_layout)
        self.model_status = QLabel(self.actionCard)
        self.model_status.setWordWrap(True)
        self.model_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.actionCardLayout.insertWidget(3, self.model_status)
        self.preview_button = QPushButton("Mostrar detalle de preparación", self.actionCard)
        self.preview_button.clicked.connect(self._show_preview_dialog)
        self.actionCardLayout.insertWidget(4, self.preview_button)
        self.refresh_summary()

    def set_compact(self, compact: bool) -> None:
        direction = (
            QBoxLayout.Direction.TopToBottom
            if compact
            else QBoxLayout.Direction.LeftToRight
        )
        self.summary_layout.setDirection(direction)
        self.actionRow.setDirection(direction)
        self.resultRow.setDirection(direction)
        self.progress.setMaximumWidth(16777215 if compact else 180)

    def set_busy(self, busy: bool) -> None:
        self.run_button.setEnabled(not busy)
        self.progress.setVisible(busy)
        if busy:
            self.progress.setMaximum(0)
            self.progress.setTextVisible(False)
            self.state_label.setText("Iniciando evaluación...")
            self.run_button.setText("…  Evaluación en curso")
        else:
            self.progress.setMaximum(100)
            self.progress.setValue(0)
            self.progress.setTextVisible(False)
            self.state_label.setText("Lista para comenzar")
            self.run_button.setText("▶  Iniciar evaluación")

    def update_progress(self, current: int, total: int) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.progress.setTextVisible(True)
        self.state_label.setText(f"Evaluando {current}/{total}...")

    def refresh(self) -> None:
        self.refresh_summary()
        reviews = self.service.get_saved_reviews()
        previous = self.review_combo.currentIndex()
        self.review_combo.blockSignals(True)
        self.review_combo.clear()
        for index, review in enumerate(reviews):
            self.review_combo.addItem(f"#{index + 1} · {review.review_date}", index)
        self.review_combo.blockSignals(False)
        if not reviews:
            text_muted_color = self.theme_manager.get_palette_color("text_muted") if self.theme_manager else "#7f93aa"
            self.result_view.setHtml(
                f"<div style='color:{text_muted_color}; padding:24px'>"
                "Aún no hay evaluaciones registradas en esta sesión."
                "</div>"
            )
            return
        self.review_combo.setCurrentIndex(min(max(previous, 0), len(reviews) - 1))
        self.show_selected_review()

    def refresh_summary(self) -> None:
        files = self.service.file_context
        requirements = self.service.get_requirements()
        reviews = self.service.get_saved_reviews()
        self.files_metric.set_value(len(files))
        self.requirements_metric.set_value(len(requirements))
        self.reviews_metric.set_value(len(reviews))
        self._refresh_model_status()

    def _preview_html(self) -> str:
        files = self.service.file_context
        requirements = self.service.get_requirements()
        file_lines = "".join(f"<li>{escape(str(file.path))}</li>" for file in files) or "<li>Sin archivos</li>"
        req_lines = "".join(
            f"<li>[{escape(req.id)}] {escape(req.description)}</li>" for req in requirements
        ) or "<li>Sin requerimientos</li>"
        return (
            f"<b>Workspace / contexto</b><ul>{file_lines}</ul>"
            f"<b>Requerimientos</b><ul>{req_lines}</ul>"
        )

    def _refresh_model_status(self) -> None:
        provider = self.service.model_provider
        is_agent = self.service.evaluation_mode == EvaluationMode.AGENT_AI
        mode = "Agente" if is_agent else "Pipeline LLM"
        provider_name = provider.current_provider.value.capitalize() if provider.current_provider else "Sin configurar"
        llm = provider.current_llm or "Sin configurar"
        details = [f"<b>Modo:</b> {mode}", f"<b>Proveedor:</b> {provider_name}", f"<b>LLM:</b> {escape(llm)}"]
        missing = []
        if not provider.is_llm_configured():
            missing.append("LLM")
        if is_agent:
            embedding = provider.current_embedding or "Sin configurar"
            details.append(f"<b>Embeddings:</b> {escape(embedding)}")
            if not provider.is_embedding_configured():
                missing.append("Embeddings")
        if missing:
            details.append(f"<b>Configuración incompleta:</b> falta {', '.join(missing)}.")
            if self.theme_manager:
                text_color = self.theme_manager.get_palette_color("warning_text")
                bg_color = self.theme_manager.get_palette_color("warning_bg")
                border_color = self.theme_manager.get_palette_color("border")
            else:
                text_color = "#765a00"
                bg_color = "#fff4c2"
                border_color = "#e6c85c"
            self.model_status.setStyleSheet(
                f"QLabel {{ color: {text_color}; background: {bg_color}; border: 1px solid {border_color}; "
                "border-radius: 8px; padding: 9px; }"
            )
        else:
            if self.theme_manager:
                text_color = self.theme_manager.get_palette_color("info_text")
                bg_color = self.theme_manager.get_palette_color("info_bg")
                border_color = self.theme_manager.get_palette_color("border")
            else:
                text_color = "#294057"
                bg_color = "#f5f8fb"
                border_color = "#d7e1eb"
            self.model_status.setStyleSheet(
                f"QLabel {{ color: {text_color}; background: {bg_color}; border: 1px solid {border_color}; "
                "border-radius: 8px; padding: 9px; }"
            )
        self.model_status.setText(" &nbsp;·&nbsp; ".join(details))

    def _show_preview_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Detalle de preparación de la evaluación")
        dialog.resize(720, 520)
        layout = QVBoxLayout(dialog)
        preview = QTextBrowser(dialog)
        preview.setHtml(self._preview_html())
        layout.addWidget(preview)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=dialog)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def export_selected_review(self) -> None:
        index = self.review_combo.currentData()
        if index is None:
            self._show_messagebox("warning", "No hay evaluación", "No hay ninguna evaluación seleccionada para exportar.")
            return
        reviews = self.service.get_saved_reviews()
        if not reviews or index < 0 or index >= len(reviews):
            return
        review = reviews[index]
        
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar informe de fidelidad",
            f"review_{review.review_date.replace(' ', '_').replace(':', '-')}.json",
            "JSON Files (*.json)",
        )
        if not filename:
            return
            
        try:
            import json
            from dataclasses import asdict
            from enum import Enum
            
            def custom_serializer(obj):
                if isinstance(obj, Enum):
                    return obj.value
                raise TypeError(f"Type {type(obj)} not serializable")
                
            data_dict = asdict(review)
            json_data = json.dumps(data_dict, indent=2, ensure_ascii=False, default=custom_serializer)
            Path(filename).write_text(json_data, encoding="utf-8")
            self._show_messagebox("info", "Exportación exitosa", f"El informe se ha exportado correctamente a {filename}")
        except Exception as error:
            self._show_messagebox("critical", "Error al exportar", str(error))

    def show_selected_review(self, _index: int = -1) -> None:
        index = self.review_combo.currentData()
        if index is None:
            return
        try:
            text = self.service.get_formatted_review(index)
        except Exception as error:
            self.result_view.setPlainText(str(error))
            return
        if self.theme_manager:
            accent = self.theme_manager.get_palette_color("accent")
            text_color = self.theme_manager.get_palette_color("text")
            bg = self.theme_manager.get_palette_color("background")
            surface = self.theme_manager.get_palette_color("surface")
            border = self.theme_manager.get_palette_color("border")
        else:
            accent, text_color, bg, surface, border = "#63e6be", "#dbe7f4", "#08111f", "#0f1c2e", "#20324a"

        cumple_color = "#16a34a" if not self.theme_manager or not self.theme_manager.is_dark else "#4ade80"
        no_cumple_color = "#dc2626" if not self.theme_manager or not self.theme_manager.is_dark else "#f87171"

        fulfilled_html = ""
        for line in text.splitlines():
            l = line.strip()
            if "cumple" in l.lower() and "no" not in l.lower():
                fulfilled_html += f'<span style="color:{cumple_color};font-weight:700;">{escape(l)}</span>\n'
            elif "no cumple" in l.lower():
                fulfilled_html += f'<span style="color:{no_cumple_color};font-weight:700;">{escape(l)}</span>\n'
            else:
                fulfilled_html += f"{escape(l)}\n"

        self.result_view.setHtml(
            f"""<style>
            body{{background:{bg};margin:0;padding:0;}}
            .card{{background:{surface};border:1px solid {border};border-radius:12px;padding:20px;margin:8px;}}
            h2{{color:{accent};margin:0 0 16px 0;font-size:18px;}}
            pre{{white-space:pre-wrap;line-height:1.7;font-family:inherit;font-size:13px;color:{text_color};margin:0;}}
            </style>
            <div class="card">
            <h2>Informe de fidelidad</h2>
            <pre>{fulfilled_html}</pre>
            </div>"""
        )

    def refresh_styles(self) -> None:
        self.refresh()

    def _show_messagebox(self, icon_type: str, title: str, text: str, buttons=None):
        if self.theme_manager:
            return self.theme_manager.show_message_box(self, icon_type, title, text, buttons)
        from PyQt6.QtWidgets import QMessageBox
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
