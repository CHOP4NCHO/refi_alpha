"""Evaluation controls and historical result viewer."""

from html import escape

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

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

    def set_busy(self, busy: bool) -> None:
        self.run_button.setEnabled(not busy)
        self.progress.setVisible(busy)
        self.state_label.setText("Evaluación en curso…" if busy else "Lista para comenzar")

    def refresh(self) -> None:
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
