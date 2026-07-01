"""Main window and UI orchestration for the PyQt6 client."""

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QThreadPool
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QButtonGroup, QLayout, QMainWindow, QMessageBox, QPushButton, QWidget

from core.exceptions import DomainError, ModelConfigurationError, ModelsNotConfiguredError

from .config_page import ConfigPage
from .evaluation_page import EvaluationPage
from .requirements_page import RequirementsPage
from .theme import LIGHT_STYLESHEET
from .ui_loader import load_ui
from .workers import ServiceWorker
from .workspace_page import WorkspacePage


class RefiMainWindow(QMainWindow):
    """A presentation-only shell whose state and operations come from RefiService."""

    def __init__(
        self,
        service,
        title: str = "REFI ALPHA",
        size: tuple[int, int] = (1280, 820),
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.service = service
        self.thread_pool = QThreadPool.globalInstance()
        self._workers: set[ServiceWorker] = set()
        self._compact_mode: bool | None = None
        self._page_titles = ["Espacio de trabajo", "Requerimientos", "Evaluación", "Configuración"]
        self._page_help = [
            "Selecciona un repositorio y arrastra archivos al contexto de evaluación.",
            "Agrega, importa, clasifica o elimina los requerimientos a comprobar.",
            "Revisa el contexto preparado, ejecuta el análisis y consulta sus informes.",
            "Configura el comportamiento, proveedor y modelos usados por la aplicación.",
        ]

        load_ui("main_window.ui", self)
        self.setWindowTitle(title)
        self.resize(*size)
        self.setMinimumSize(720, 560)
        self.setStyleSheet(LIGHT_STYLESHEET)
        self._setup_ui()
        self._connect_pages()
        self.log_message("Sistema listo. La interfaz PyQt6 está conectada a RefiService.")

    def _setup_ui(self) -> None:
        navigation = QButtonGroup(self)
        navigation.setExclusive(True)
        self.nav_buttons = (
            self.workspaceNavButton,
            self.requirementsNavButton,
            self.evaluationNavButton,
            self.configNavButton,
        )
        for index, button in enumerate(self.nav_buttons):
            button.clicked.connect(lambda checked=False, page=index: self.show_page(page))
            navigation.addButton(button, index)
        self.menu_button = QPushButton("☰", self.header)
        self.menu_button.setToolTip("Mostrar u ocultar la navegación")
        self.menu_button.setFixedWidth(42)
        self.menu_button.clicked.connect(self._toggle_sidebar)
        self.headerLayout.insertWidget(0, self.menu_button)
        self.page_title.setObjectName("pageTitle")
        self.page_title.setMinimumWidth(0)
        self.page_title.setMaximumWidth(16777215)
        self.titleLayout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.info_button.clicked.connect(self._show_page_help)

        self.workspace_page = WorkspacePage(self.service)
        self.requirements_page = RequirementsPage(self.service)
        self.evaluation_page = EvaluationPage(self.service)
        self.config_page = ConfigPage(self.service)
        for page in (
            self.workspace_page,
            self.requirements_page,
            self.evaluation_page,
            self.config_page,
        ):
            self.pages.addWidget(page)
        self.console_toggle.toggled.connect(self._toggle_console)
        self.consoleTitle.setObjectName("sectionTitle")
        self.statusBar().setSizeGripEnabled(True)
        self._apply_responsive_layout(self.width())

    def _connect_pages(self) -> None:
        self.workspace_page.message.connect(self.log_message)
        self.workspace_page.context_changed.connect(self.evaluation_page.refresh_summary)
        self.requirements_page.message.connect(self.log_message)
        self.requirements_page.requirements_changed.connect(self.evaluation_page.refresh_summary)
        self.requirements_page.import_requested.connect(self.start_pdf_import)
        self.evaluation_page.evaluation_requested.connect(self.start_evaluation)
        self.config_page.message.connect(self.log_message)
        self.config_page.message.connect(lambda _message: self.evaluation_page.refresh_summary())

    def show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.page_title.setText(self._page_titles[index])
        if index == 2:
            self.evaluation_page.refresh()
        if self._compact_mode:
            self.sidebar.hide()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "sidebar") and hasattr(self, "workspace_page"):
            self._apply_responsive_layout(event.size().width())

    def _apply_responsive_layout(self, width: int) -> None:
        compact = width < 980
        if compact != self._compact_mode:
            self._compact_mode = compact
            self.sidebar.setVisible(not compact)
            self.menu_button.setVisible(compact)
        self.theme_button.setVisible(width >= 820)
        margin = 12 if compact else 24
        self.bodyLayout.setContentsMargins(margin, 12 if compact else 20, margin, 12)
        self.console.setMaximumHeight(90 if compact else 125)
        self.workspace_page.set_compact(compact)
        self.requirements_page.set_compact(compact)
        self.evaluation_page.set_compact(compact)
        self.config_page.set_compact(compact)

    def _toggle_sidebar(self) -> None:
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def _toggle_console(self, hidden: bool) -> None:
        self.console.setVisible(not hidden)
        self.console_toggle.setText("Mostrar" if hidden else "Ocultar")

    def _show_page_help(self) -> None:
        index = self.pages.currentIndex()
        QMessageBox.information(self, f"Uso de {self._page_titles[index]}", self._page_help[index])

    def log_message(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.appendPlainText(f"{timestamp}  {message}")
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def start_pdf_import(self, path: Path) -> None:
        self.log_message(f"Iniciando extracción desde PDF: {path}")
        worker = ServiceWorker(lambda _log: self.service.extract_requirements_from_pdf(path))
        worker.signals.succeeded.connect(self._pdf_import_succeeded)
        worker.signals.failed.connect(self._pdf_import_failed)
        self._start_worker(worker)

    def _pdf_import_succeeded(self, document) -> None:
        self.requirements_page.finish_import(document=document)
        count = len(document.requirements)
        self.log_message(f"Extracción completada: {count} requerimiento(s) cargado(s).")
        self.evaluation_page.refresh_summary()
        QMessageBox.information(self, "Extracción completada", f"Se cargaron {count} requerimiento(s).")

    def _pdf_import_failed(self, error: Exception, trace: str) -> None:
        self.requirements_page.finish_import(error=str(error))
        self._present_error(error, trace, "Error de extracción")

    def start_evaluation(self) -> None:
        if not self.service.get_requirements():
            QMessageBox.warning(self, "Sin requerimientos", "Agrega al menos un requerimiento antes de evaluar.")
            return
        if not self.service.file_context:
            QMessageBox.warning(self, "Sin contexto", "Incluye al menos un archivo de código antes de evaluar.")
            return
        answer = QMessageBox.question(
            self,
            "Iniciar evaluación",
            f"Se evaluarán {len(self.service.get_requirements())} requerimiento(s) contra "
            f"{len(self.service.file_context)} archivo(s). ¿Continuar?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.evaluation_page.set_busy(True)
        self.log_message("Evaluación iniciada.")
        worker = ServiceWorker(lambda log: self.service.evaluate(log_callback=log))
        worker.signals.log.connect(self.log_message)
        worker.signals.succeeded.connect(self._evaluation_succeeded)
        worker.signals.failed.connect(self._evaluation_failed)
        self._start_worker(worker)

    def _evaluation_succeeded(self, _result) -> None:
        self.evaluation_page.set_busy(False)
        self.evaluation_page.refresh()
        self.requirements_page.refresh()
        self.evaluation_page.refresh_summary()
        output = self.service.result_manager.default_save_path / self.service.result_manager.default_save_name
        self.log_message(f"Evaluación completada. Resultados guardados en: {output}")
        QMessageBox.information(self, "Evaluación completada", "El informe se generó correctamente.")

    def _evaluation_failed(self, error: Exception, trace: str) -> None:
        self.evaluation_page.set_busy(False)
        self._present_error(error, trace, "No se pudo evaluar")

    def _start_worker(self, worker: ServiceWorker) -> None:
        self._workers.add(worker)
        worker.signals.finished.connect(lambda current=worker: self._workers.discard(current))
        self.thread_pool.start(worker)

    def _present_error(self, error: Exception, trace: str, title: str) -> None:
        if isinstance(error, ModelsNotConfiguredError):
            message = (
                f"Faltan modelos para la operación '{error.operation}': "
                f"{', '.join(error.missing_models)}. Revisa Configuración."
            )
        elif isinstance(error, ModelConfigurationError):
            message = f"Problema con el modelo {error.model_type.upper()}: {error.message}"
        elif isinstance(error, DomainError):
            message = str(error)
        else:
            message = str(error) or "Ocurrió un error inesperado."
        self.log_message(f"ERROR: {message}")
        if not isinstance(error, DomainError):
            self.log_message(trace)
        QMessageBox.critical(self, title, message)
