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

    def __init__(self, service, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        load_ui("evaluation_page.ui", self)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        self.run_button.clicked.connect(self.evaluation_requested)
        self.review_combo.currentIndexChanged.connect(self.show_selected_review)
        self.refresh_button.clicked.connect(self.refresh)
        self.state_label.hide()
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
        self.run_button.setText("…  Evaluación en curso" if busy else "▶  Iniciar evaluación")

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
            self.result_view.setHtml(
                "<div style='color:#7f93aa; padding:24px'>"
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
            self.model_status.setStyleSheet(
                "QLabel { color: #765a00; background: #fff4c2; border: 1px solid #e6c85c; "
                "border-radius: 8px; padding: 9px; }"
            )
        else:
            self.model_status.setStyleSheet(
                "QLabel { color: #294057; background: #f5f8fb; border: 1px solid #d7e1eb; "
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

    def show_selected_review(self, _index: int = -1) -> None:
        index = self.review_combo.currentData()
        if index is None:
            return
        try:
            text = self.service.get_formatted_review(index)
        except Exception as error:
            self.result_view.setPlainText(str(error))
            return
        self.result_view.setHtml(
            "<style>pre{white-space:pre-wrap;line-height:1.5;}"
            "h3{color:#63e6be}</style>"
            f"<h3>Informe de fidelidad</h3><pre>{escape(text)}</pre>"
        )
