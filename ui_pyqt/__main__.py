"""Run the PyQt6 edition with ``python -m ui_pyqt``."""

import logging
import sys

from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

from core import RefiService
from core.enums import EvaluationMode, RealEvaluation
from core.model_provider import ModelProvider

from .main_window import RefiMainWindow


def main() -> int:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app = QApplication(sys.argv)
    app.setApplicationName("REFI ALPHA")
    app.setOrganizationName("REFI")

    model_provider = ModelProvider(
        local_ip="localhost",
        cloud_ip="generativelanguage.googleapis.com/v1beta/openai",
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
    window = RefiMainWindow(service=service)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
