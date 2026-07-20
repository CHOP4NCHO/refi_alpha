"""Main window and UI orchestration for the PyQt6 client."""

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QThreadPool, pyqtSignal
from PyQt6.QtGui import QPixmap, QResizeEvent
from PyQt6.QtWidgets import QButtonGroup, QLayout, QMainWindow, QMessageBox, QPushButton, QWidget

from core.exceptions import DomainError, ModelConfigurationError, ModelsNotConfiguredError

from .config_page import ConfigPage
from .evaluation_page import EvaluationPage
from .requirements_page import RequirementsPage
from .review_viewer_page import ReviewViewerPage
from .theme_manager import ThemeManager
from .ui_loader import load_ui
from .workers import ServiceWorker
from .workspace_page import WorkspacePage


class RefiMainWindow(QMainWindow):
    """A presentation-only shell whose state and operations come from RefiService."""

    back_to_landing = pyqtSignal()

    def __init__(
        self,
        service,
        title: str = "REFI ALPHA",
        size: tuple[int, int] = (1280, 820),
        parent: QWidget | None = None,
        theme_manager: ThemeManager | None = None,
        mode: str = "evaluation",
        review_data: dict | None = None,
    ):
        super().__init__(parent)
        self.service = service
        self.mode = mode
        self.review_data = review_data
        if theme_manager is None:
            theme_manager = ThemeManager()
        self.theme_manager = theme_manager
        self.thread_pool = QThreadPool.globalInstance()
        self._workers: set[ServiceWorker] = set()
        self._compact_mode: bool | None = None
        self._page_titles = ["Espacio de trabajo", "Requerimientos", "Evaluación", "Configuración", "Revisión"]
        self._page_help = [
            "Selecciona un repositorio y arrastra archivos al contexto de evaluación.",
            "Agrega, importa, clasifica o elimina los requerimientos a comprobar.",
            "Revisa el contexto preparado, ejecuta el análisis y consulta sus informes.",
            "Configura el comportamiento, proveedor y modelos usados por la aplicación.",
            "Consulta los resultados de una evaluación previamente exportada.",
        ]

        load_ui("main_window.ui", self)
        self.setWindowTitle(title)
        self.resize(*size)
        self.setMinimumSize(720, 560)
        self.theme_manager.apply_to(self)
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

        self.back_button = QPushButton("← Volver", self.header)
        self.back_button.setToolTip("Volver a la pantalla de inicio")
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_button.clicked.connect(self.back_to_landing.emit)
        self.back_button.setVisible(False)
        self.headerLayout.insertWidget(0, self.back_button)

        self.sidebar_back_button = QPushButton("← Volver al inicio", self.sidebar)
        self.sidebar_back_button.setToolTip("Volver a la pantalla de inicio")
        self.sidebar_back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_back_button.clicked.connect(self.back_to_landing.emit)
        self.sidebarLayout.insertWidget(3, self.sidebar_back_button)

        self._setup_brand_logo()
        self.page_title.setObjectName("pageTitle")
        self.page_title.setMinimumWidth(0)
        self.page_title.setMaximumWidth(16777215)
        self.titleLayout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.info_button.clicked.connect(self._show_page_help)
        self.theme_button.clicked.connect(self._toggle_theme)
        self._update_theme_button_text()

        self.workspace_page = WorkspacePage(self.service, theme_manager=self.theme_manager)
        self.requirements_page = RequirementsPage(self.service, theme_manager=self.theme_manager)
        self.evaluation_page = EvaluationPage(self.service, theme_manager=self.theme_manager)
        self.config_page = ConfigPage(self.service, theme_manager=self.theme_manager)
        for page in (
            self.workspace_page,
            self.requirements_page,
            self.evaluation_page,
            self.config_page,
        ):
            self.pages.addWidget(page)

        self.review_viewer_page = None
        if self.mode == "review" and self.review_data is not None:
            self.review_viewer_page = ReviewViewerPage(
                self.review_data, theme_manager=self.theme_manager
            )
            self.review_viewer_page.back_requested.connect(self.back_to_landing.emit)
            self.pages.addWidget(self.review_viewer_page)

        self.console_toggle.toggled.connect(self._toggle_console)
        self.consoleTitle.setObjectName("sectionTitle")
        self.statusBar().setSizeGripEnabled(True)

        if self.mode == "review":
            self._apply_review_mode()
        else:
            self.consoleCard.setVisible(False)
            self._apply_responsive_layout(self.width())

    def _setup_brand_logo(self) -> None:
        logo_path = Path(__file__).with_name("refi.png")
        logo = QPixmap(str(logo_path))
        if logo.isNull():
            return
        self.brandMark.setText("")
        self.brandMark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brandMark.setPixmap(
            logo.scaled(
                128,
                128,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.brandMark.setMinimumHeight(128)

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
        self.consoleCard.setVisible(index == 2)
        if index == 2:
            self.evaluation_page.refresh()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self.mode == "review":
            return
        if hasattr(self, "sidebar") and hasattr(self, "workspace_page"):
            self._apply_responsive_layout(event.size().width())

    def _apply_review_mode(self) -> None:
        self.sidebar.setVisible(False)
        self.menu_button.setVisible(False)
        self.back_button.setVisible(True)
        self.consoleCard.setVisible(False)
        self.info_button.setVisible(False)
        self.pages.setCurrentIndex(4)
        self.page_title.setText("Revisión de evaluación")

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
        self._show_messagebox("info", f"Uso de {self._page_titles[index]}", self._page_help[index])

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
        self._show_messagebox("info", "Extracción completada", f"Se cargaron {count} requerimiento(s).")

    def _pdf_import_failed(self, error: Exception, trace: str) -> None:
        self.requirements_page.finish_import(error=str(error))
        self._present_error(error, trace, "Error de extracción")

    def start_evaluation(self) -> None:
        if not self.service.get_requirements():
            self._show_messagebox("warning", "Sin requerimientos", "Agrega al menos un requerimiento antes de evaluar.")
            return
        if not self.service.file_context:
            self._show_messagebox("warning", "Sin contexto", "Incluye al menos un archivo de código antes de evaluar.")
            return
        answer = self._show_messagebox(
            "question",
            "Iniciar evaluación",
            f"Se evaluarán {len(self.service.get_requirements())} requerimiento(s) contra "
            f"{len(self.service.file_context)} archivo(s). ¿Continuar?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.evaluation_page.set_busy(True)
        self.log_message("Evaluación iniciada.")
        worker = ServiceWorker(lambda log: self.service.evaluate(
            log_callback=log,
            progress_callback=lambda current, total: worker.signals.progress.emit(current, total)
        ))
        worker.signals.log.connect(self.log_message)
        worker.signals.progress.connect(self.evaluation_page.update_progress)
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
        self._show_messagebox("info", "Evaluación completada", "El informe se generó correctamente.")

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
        self._show_messagebox("critical", title, message)

    def _toggle_theme(self) -> None:
        self.theme_manager.toggle()
        self.theme_manager.apply_to(self)
        self._update_theme_button_text()
        if hasattr(self, "config_page"):
            self.config_page.update_theme_ui()
        if hasattr(self, "evaluation_page"):
            self.evaluation_page.refresh_styles()

    def _update_theme_button_text(self) -> None:
        if self.theme_manager.is_dark:
            self.theme_button.setText("🌙  Modo oscuro")
        else:
            self.theme_button.setText("☀  Modo claro")

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
