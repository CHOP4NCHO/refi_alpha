"""Application and model configuration page."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QMessageBox,
    QWidget,
)

from core.enums import EvaluationMode, LlmProvider, RealEvaluation

from .ui_loader import load_ui


class ConfigPage(QWidget):
    message = pyqtSignal(str)

    def __init__(self, service, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self._models_cache = []
        self._loading = True
        load_ui("config_page.ui", self)
        self._setup_ui()
        self._load_state()
        self._loading = False

    def _setup_ui(self) -> None:
        self.debug_check.toggled.connect(self._set_debug)
        for value in EvaluationMode:
            self.eval_mode_combo.addItem(self._evaluation_label(value), value)
        self.eval_mode_combo.currentIndexChanged.connect(self._set_evaluation_mode)
        for value in RealEvaluation:
            self.real_eval_combo.addItem(self._real_evaluation_label(value), value)
        self.real_eval_combo.currentIndexChanged.connect(self._set_real_evaluation)
        for provider in LlmProvider:
            self.provider_combo.addItem(provider.value.capitalize(), provider)
        self.provider_combo.currentIndexChanged.connect(self._provider_changed)
        self.llm_combo.currentIndexChanged.connect(self._set_llm)
        self.vlm_combo.currentIndexChanged.connect(self._set_vlm)
        self.embedding_combo.currentIndexChanged.connect(self._set_embedding)

    def _load_state(self) -> None:
        provider = self.service.model_provider.current_provider or LlmProvider.GEMINI
        self._select_data(self.provider_combo, provider)
        self.debug_check.setChecked(self.service.debug_mode)
        self._select_data(self.eval_mode_combo, self.service.evaluation_mode)
        self._select_data(self.real_eval_combo, self.service.real_evaluation)
        self._refresh_models()

    def _refresh_models(self) -> None:
        provider = self.provider_combo.currentData()
        try:
            models = self.service.model_provider.list_models()
        except Exception as error:
            QMessageBox.warning(self, "Modelos no disponibles", str(error))
            models = []
        self._models_cache = [model for model in models if model.provider == provider]
        mappings = (
            (self.llm_combo, "chat", self.service.model_provider.current_llm),
            (self.vlm_combo, "vlm", self.service.model_provider.current_vlm),
            (self.embedding_combo, "embedding", self.service.model_provider.current_embedding),
        )
        for combo, category, current in mappings:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Sin configurar", None)
            for model in self._models_cache:
                if model.category == category:
                    combo.addItem(model.model_id, model)
            if current:
                for index in range(combo.count()):
                    model = combo.itemData(index)
                    if model and model.model_id == current:
                        combo.setCurrentIndex(index)
                        break
            combo.blockSignals(False)
        reachable = self.service.model_provider.is_ollama_reachable
        self.connection_label.setText(
            "● Ollama disponible" if reachable else "○ Ollama no disponible · Los modelos Gemini siguen accesibles"
        )

    def _provider_changed(self, _index: int) -> None:
        if not self._loading:
            self._refresh_models()

    def _set_debug(self, checked: bool) -> None:
        if self._loading:
            return
        self.service.debug_mode = checked
        self.message.emit(f"Modo debug {'activado' if checked else 'desactivado'}.")

    def _set_evaluation_mode(self, _index: int) -> None:
        mode = self.eval_mode_combo.currentData()
        if mode is not None and not self._loading:
            self.service.evaluation_mode = mode
            self.message.emit(f"Estrategia seleccionada: {self._evaluation_label(mode)}.")

    def _set_real_evaluation(self, _index: int) -> None:
        value = self.real_eval_combo.currentData()
        if value is not None and not self._loading:
            self.service.real_evaluation = value

    def _set_llm(self, _index: int) -> None:
        model = self.llm_combo.currentData()
        if model is None or self._loading:
            return
        try:
            self.service.model_provider.set_llm(model)
            self.service._update_evaluator_llm()
            self.message.emit(f"LLM configurado: {model.model_id}")
        except Exception as error:
            QMessageBox.critical(self, "No se pudo configurar", str(error))

    def _set_vlm(self, _index: int) -> None:
        model = self.vlm_combo.currentData()
        if model is None or self._loading:
            return
        try:
            self.service.model_provider.set_vlm(model)
            self.service._reset_requirements_extractor()
            self.message.emit(f"VLM configurado: {model.model_id}")
        except Exception as error:
            QMessageBox.critical(self, "No se pudo configurar", str(error))

    def _set_embedding(self, _index: int) -> None:
        model = self.embedding_combo.currentData()
        if model is None or self._loading:
            return
        try:
            self.service.model_provider.set_embedding(model)
            self.service._reset_requirements_extractor()
            self.message.emit(f"Embeddings configurados: {model.model_id}")
        except Exception as error:
            QMessageBox.critical(self, "No se pudo configurar", str(error))

    @staticmethod
    def _select_data(combo: QComboBox, value) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return

    @staticmethod
    def _evaluation_label(value: EvaluationMode) -> str:
        return "Agente con recuperación semántica" if value == EvaluationMode.AGENT_AI else "Pipeline LLM"

    @staticmethod
    def _real_evaluation_label(value: RealEvaluation) -> str:
        return "Cumplido" if value == RealEvaluation.FULFILLED else "No cumplido"
