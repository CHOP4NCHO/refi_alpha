"""Small QRunnable adapter used for long-running service operations."""

import traceback
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot


class WorkerSignals(QObject):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(object, str)
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    finished = pyqtSignal()


class ServiceWorker(QRunnable):
    def __init__(self, operation: Callable[[Callable[[str], None]], Any]):
        super().__init__()
        self.operation = operation
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            result = self.operation(self.signals.log.emit)
        except Exception as error:  # The UI presents domain errors on the main thread.
            self.signals.failed.emit(error, traceback.format_exc())
        else:
            self.signals.succeeded.emit(result)
        finally:
            self.signals.finished.emit()
