"""Application and model configuration page."""

import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QMessageBox,
    QLineEdit,
    QWidget,
)

from core.enums import EvaluationMode, LlmProvider, RealEvaluation

from .ui_loader import load_ui


class ConfigPage(QWidget):
    message = pyqtSignal(str)

    def __init__(self, service, parent: QWidget | None = None, theme_manager=None):
        super().__init__(parent)
        self.service = service
        self.theme_manager = theme_manager
        self._models_cache = []
        self._loading = True
        load_ui("config_page.ui", self)
        self._setup_ui()
        self._load_state()
        self._loading = False

    def _setup_ui(self) -> None:
        self.debugLabel.setText("Modo Debug")
        tooltips = {
            self.provider_combo: "Servicio que suministra los modelos disponibles.",
            self.ollama_host_input: "Host o IP donde Ollama expone su API local.",
            self.ollama_verify_button: "Comprueba si Ollama responde y actualiza el catálogo local.",
            self.gemini_key_input: "Clave del proveedor cloud usada solo durante esta sesión.",
            self.gemini_apply_button: "Carga la clave en memoria para usar modelos cloud.",
            self.llm_combo: "Modelo de lenguaje que evalúa el cumplimiento de los requerimientos.",
            self.vlm_combo: "Modelo visual utilizado para interpretar documentos PDF.",
            self.embedding_combo: "Modelo que convierte texto en vectores para la búsqueda semántica.",
        }
        for widget, tooltip in tooltips.items():
            widget.setToolTip(tooltip)
        self.gemini_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key_input.setPlaceholderText("API key")
        self.ollama_host_input.setPlaceholderText("localhost")
        self.ollama_verify_button.clicked.connect(self._verify_ollama)
        self.gemini_apply_button.clicked.connect(self._apply_cloud_key)
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
        
        # Add theme combo box row
        self.theme_combo = QComboBox(self)
        self.theme_combo.addItem("Claro", "light")
        self.theme_combo.addItem("Oscuro", "dark")
        self.theme_combo.currentIndexChanged.connect(self._theme_changed)
        self.generalForm.addRow("Tema visual", self.theme_combo)
        self.update_theme_ui()

    def set_compact(self, compact: bool) -> None:
        policy = (
            QFormLayout.RowWrapPolicy.WrapAllRows
            if compact
            else QFormLayout.RowWrapPolicy.DontWrapRows
        )
        self.generalForm.setRowWrapPolicy(policy)
        self.modelForm.setRowWrapPolicy(policy)

    def _load_state(self) -> None:
        provider = self.service.model_provider.current_provider or LlmProvider.GEMINI
        self._select_data(self.provider_combo, provider)
        self.ollama_host_input.setText(getattr(self.service.model_provider, "_local_ip", "localhost"))
        self._update_cloud_key_placeholder(provider)
        self.debug_check.setChecked(self.service.debug_mode)
        self._select_data(self.eval_mode_combo, self.service.evaluation_mode)
        self._select_data(self.real_eval_combo, self.service.real_evaluation)
        self._sync_vendor_controls()
        self._refresh_models()

    def _refresh_models(self) -> None:
        provider = self.provider_combo.currentData()
        models = self._safe_operation(self.service.model_provider.list_models, "Modelos no disponibles") or []
        self._models_cache = [model for model in models if model.provider == provider]
        mappings = (
            (self.llm_combo, "chat", self.service.model_provider.current_llm),
            (self.vlm_combo, "vlm", self.service.model_provider.current_vlm),
            (self.embedding_combo, "embedding", self.service.model_provider.current_embedding),
        )
        for combo, category, current_id in mappings:
            items = [("Sin configurar", None)]
            for model in self._models_cache:
                if model.category == category:
                    items.append((model.model_id, model))
            
            current_model = None
            if current_id:
                for label, data in items:
                    if data and data.model_id == current_id:
                        current_model = data
                        break
            self._populate_combo(combo, items, current_model)
        self._update_status_labels()

    def _provider_changed(self, _index: int) -> None:
        if not self._loading:
            self._sync_vendor_controls()
            self._refresh_models()

    def _sync_vendor_controls(self) -> None:
        provider = self.provider_combo.currentData()
        is_ollama = provider == LlmProvider.OLLAMA
        self.ollamaHostLabel.setVisible(is_ollama)
        self.ollama_host_container.setVisible(is_ollama)
        self.geminiKeyLabel.setVisible(not is_ollama)
        self.gemini_key_container.setVisible(not is_ollama)
        if not is_ollama:
            self._update_cloud_key_placeholder(provider)
        self._update_status_labels()

    def _verify_ollama(self) -> None:
        host = self.ollama_host_input.text().strip() or "localhost"
        try:
            self.service.model_provider.set_ollama_ip(host)
            self._select_data(self.provider_combo, LlmProvider.OLLAMA)
            self._refresh_models()
            if self.service.model_provider.is_ollama_reachable:
                self.message.emit(f"Ollama disponible en {host}. Catálogo actualizado.")
            else:
                self.message.emit(f"Ollama no disponible en {host}.")
        except Exception as error:
            self._show_messagebox("critical", "No se pudo verificar Ollama", str(error))
        finally:
            self._update_status_labels()

    def _apply_cloud_key(self) -> None:
        provider = self.provider_combo.currentData()
        env_key = self._provider_env_key(provider)
        api_key = self.gemini_key_input.text().strip()
        if not api_key:
            self._show_messagebox(
                "warning",
                "Credencial requerida",
                f"Ingresa {env_key} para usar modelos {self._provider_display(provider)}.",
            )
            self._update_status_labels()
            return
        os.environ[env_key] = api_key
        self.gemini_key_input.clear()
        self._update_cloud_key_placeholder(provider)
        self._refresh_models()
        self.message.emit(f"Credencial {self._provider_display(provider)} cargada en memoria para esta sesión.")

    def _update_status_labels(self) -> None:
        provider = self.provider_combo.currentData()
        ollama_reachable = self.service.model_provider.is_ollama_reachable
        if provider == LlmProvider.OLLAMA:
            host = self.ollama_host_input.text().strip() or "localhost"
            vendor_status = f"Ollama disponible en {host}" if ollama_reachable else f"Ollama no disponible en {host}"
            credential_status = "Credenciales locales no requeridas."
        else:
            env_key = self._provider_env_key(provider)
            provider_name = self._provider_display(provider)
            provider_ready = bool(os.environ.get(env_key))
            vendor_status = (
                f"{provider_name} listo para activación"
                if provider_ready
                else f"{provider_name} requiere {env_key}."
            )
            credential_status = "Credencial cargada en memoria." if provider_ready else "Credencial no cargada."
        self.connection_label.setText(vendor_status)
        self.credential_status_label.setText(credential_status)
        active_parts = [
            f"LLM: {self.service.model_provider.current_llm or 'sin configurar'}",
            f"VLM: {self.service.model_provider.current_vlm or 'sin configurar'}",
            f"Embeddings: {self.service.model_provider.current_embedding or 'sin configurar'}",
        ]
        self.active_models_label.setText("Modelos activos - " + " | ".join(active_parts))

    def _can_activate_model(self, model) -> bool:
        if model.provider == LlmProvider.CLAUDE and model.category in {"embedding", "vlm"}:
            self._show_messagebox(
                "warning",
                "Categoría no soportada",
                "Claude se puede usar como LLM en esta app. Para embeddings o VLM de importación PDF usa OpenAI, Gemini u Ollama.",
            )
            self._refresh_models()
            return False
        if model.provider != LlmProvider.OLLAMA and not os.environ.get(self._provider_env_key(model.provider)):
            self._show_messagebox(
                "warning",
                "Credencial requerida",
                f"Carga {self._provider_env_key(model.provider)} antes de activar modelos {self._provider_display(model.provider)}.",
            )
            self._refresh_models()
            return False
        if model.provider == LlmProvider.OLLAMA and not self.service.model_provider.is_ollama_reachable:
            self._show_messagebox(
                "warning",
                "Vendor no disponible",
                "Verifica la conexión con Ollama antes de activar modelos locales.",
            )
            self._refresh_models()
            return False
        return True

    def _selected_or_custom_model(self, combo: QComboBox, category: str) -> ModelConfig | None:
        model = combo.currentData()
        if model is not None:
            return model
        return None

    def _update_cloud_key_placeholder(self, provider: LlmProvider | None) -> None:
        env_key = self._provider_env_key(provider)
        if os.environ.get(env_key):
            self.gemini_key_input.setPlaceholderText(f"{env_key} cargada en esta sesión")
        else:
            self.gemini_key_input.setPlaceholderText(env_key)
        self.geminiKeyLabel.setText(f"Credencial {self._provider_display(provider)}")

    @staticmethod
    def _provider_env_key(provider: LlmProvider | None) -> str:
        env_keys = {
            LlmProvider.GEMINI: "GOOGLE_API_KEY",
            LlmProvider.OPENAI: "OPENAI_API_KEY",
            LlmProvider.CLAUDE: "ANTHROPIC_API_KEY",
        }
        return env_keys.get(provider, "API_KEY")

    @staticmethod
    def _provider_display(provider: LlmProvider | None) -> str:
        names = {
            LlmProvider.GEMINI: "Gemini",
            LlmProvider.OPENAI: "OpenAI",
            LlmProvider.CLAUDE: "Claude",
            LlmProvider.OLLAMA: "Ollama",
        }
        return names.get(provider, "Proveedor")

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
        model = self._selected_or_custom_model(self.llm_combo, "chat")
        if model is None or self._loading:
            return
        if not self._can_activate_model(model):
            return
        try:
            self.service.model_provider.set_llm(model)
            self.service.update_evaluator_llm()
            self._update_status_labels()
            self.message.emit(f"LLM activo: {model.model_id}")
        except Exception as error:
            self._show_messagebox("critical", "No se pudo configurar", str(error))

    def _set_vlm(self, _index: int) -> None:
        model = self._selected_or_custom_model(self.vlm_combo, "vlm")
        if model is None or self._loading:
            return
        if not self._can_activate_model(model):
            return
        try:
            self.service.model_provider.set_vlm(model)
            self.service.reset_requirements_extractor()
            self._update_status_labels()
            self.message.emit(f"VLM activo: {model.model_id}")
        except Exception as error:
            self._show_messagebox("critical", "No se pudo configurar", str(error))

    def _set_embedding(self, _index: int) -> None:
        model = self._selected_or_custom_model(self.embedding_combo, "embedding")
        if model is None or self._loading:
            return
        if not self._can_activate_model(model):
            return
        try:
            self.service.model_provider.set_embedding(model)
            self.service.reset_requirements_extractor()
            self._update_status_labels()
            self.message.emit(f"Embeddings activos: {model.model_id}")
        except Exception as error:
            self._show_messagebox("critical", "No se pudo configurar", str(error))

    def _theme_changed(self) -> None:
        if not self.theme_manager:
            return
        mode = self.theme_combo.currentData()
        if mode and mode != self.theme_manager.mode:
            self.theme_manager.set_mode(mode)
            main_win = self.window()
            if main_win:
                self.theme_manager.apply_to(main_win)
                if hasattr(main_win, "_update_theme_button_text"):
                    main_win._update_theme_button_text()
                if hasattr(main_win, "evaluation_page") and hasattr(main_win.evaluation_page, "refresh_styles"):
                    main_win.evaluation_page.refresh_styles()

    def update_theme_ui(self) -> None:
        if not self.theme_manager:
            return
        self.theme_combo.blockSignals(True)
        idx = self.theme_combo.findData(self.theme_manager.mode)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.blockSignals(False)

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
