"""Run the PyQt6 edition with ``python -m ui_pyqt``."""

import ctypes
import logging
import os
from pathlib import Path
import sys

#from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtGui import QIcon

from core import RefiService
from core.enums import EvaluationMode, RealEvaluation
from core.model_provider import ModelProvider

if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle - use absolute imports
    from ui_pyqt.landing_page import LandingPage
    from ui_pyqt.main_window import RefiMainWindow
    from ui_pyqt.theme_manager import ThemeManager
else:
    # Running as normal Python package - use relative imports
    from .landing_page import LandingPage
    from .main_window import RefiMainWindow
    from .theme_manager import ThemeManager


def get_resource_path(relative_path: str) -> str:
    """Obtiene la ruta absoluta para recursos (funciona en dev y PyInstaller)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)


class LandingWindow(QMainWindow):
    """Shell that shows the landing page and spawns RefiMainWindow on demand."""

    def __init__(self, service, theme_manager, icon_path):
        super().__init__()
        self.service = service
        self.theme_manager = theme_manager
        self.icon_path = icon_path
        self.main_window = None

        self.setWindowTitle("REFI ALPHA")
        self.resize(800, 600)
        self.setMinimumSize(800, 600)

        self.landing = LandingPage(service=service, theme_manager=theme_manager)
        self.setCentralWidget(self.landing)
        self.theme_manager.apply_theme()

        self.landing.new_evaluation_requested.connect(self._open_evaluation)
        self.landing.review_loaded.connect(self._open_review)

    def _open_evaluation(self) -> None:
        self.main_window = RefiMainWindow(
            service=self.service,
            theme_manager=self.theme_manager,
            mode="evaluation",
        )
        self.main_window.setWindowIcon(QIcon(self.icon_path))
        self.main_window.back_to_landing.connect(self._back_to_landing)
        self.main_window.show()
        self.hide()

    def _open_review(self, data: dict) -> None:
        self.main_window = RefiMainWindow(
            service=self.service,
            theme_manager=self.theme_manager,
            mode="review",
            review_data=data,
        )
        self.main_window.setWindowIcon(QIcon(self.icon_path))
        self.main_window.back_to_landing.connect(self._back_to_landing)
        self.main_window.show()
        self.hide()

    def _back_to_landing(self) -> None:
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        self.theme_manager.apply_theme()
        self.show()


def main() -> int:
    if sys.platform == "win32":
        myappid = "refi.alpha.ui.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    #load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app = QApplication(sys.argv)
    app.setApplicationName("REFI ALPHA")
    app.setOrganizationName("REFI")

    icon_path = get_resource_path("ui_pyqt/refi.png")
    app.setWindowIcon(QIcon(icon_path))

    # inits Model Provider
    model_provider = ModelProvider(
        temperature=0.1,
    )
    # inits REFI's FACADE
    service = RefiService(
        workdir=Path.home(),
        model_provider=model_provider,
        debug_mode=True,
        evaluation_mode=EvaluationMode.AGENT_AI,
        real_evaluation=RealEvaluation.FULFILLED,
    )
    theme_manager = ThemeManager()

    window = LandingWindow(service=service, theme_manager=theme_manager, icon_path=icon_path)
    window.setWindowIcon(QIcon(icon_path))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
