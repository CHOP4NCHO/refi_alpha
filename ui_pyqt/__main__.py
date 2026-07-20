"""Run the PyQt6 edition with ``python -m ui_pyqt``."""

import ctypes
import logging
import os
import sys

from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from core import RefiService
from core.enums import EvaluationMode, RealEvaluation
from core.model_provider import ModelProvider

from .main_window import RefiMainWindow
from .theme_manager import ThemeManager


def get_resource_path(relative_path: str) -> str:
    """Obtiene la ruta absoluta para recursos (funciona en dev y PyInstaller)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)


def main() -> int:
    if sys.platform == "win32":
        myappid = "refi.alpha.ui.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app = QApplication(sys.argv)
    app.setApplicationName("REFI ALPHA")
    app.setOrganizationName("REFI")

    icon_path = get_resource_path("refi.png")
    app.setWindowIcon(QIcon(icon_path))

    model_provider = ModelProvider(
        temperature=0.1,
    )
    service = RefiService(
        workdir=".",
        codebase_name="REFI_SOURCE_CODE",
        model_provider=model_provider,
        debug_mode=True,
        evaluation_mode=EvaluationMode.AGENT_AI,
        real_evaluation=RealEvaluation.FULFILLED,
    )
    theme_manager = ThemeManager()
    window = RefiMainWindow(service=service, theme_manager=theme_manager)
    window.setWindowIcon(QIcon(icon_path)) 
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())