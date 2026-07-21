"""Application and model configuration page."""

import os
from dataclasses import dataclass

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLineEdit,
    QWidget,
)

from core.enums import EvaluationMode, LlmProvider, RealEvaluation
from core.model_config import ModelConfig

from .ui_loader import load_ui


@dataclass
class CategorySlot:
    """Holds references to the UI widgets for one model category."""
    vendor_combo: QComboBox
    ollama_host_label: QWidget
    ollama_host_container: QWidget
    ollama_host_input: QLineEdit
    ollama_verify_button: QWidget
    key_label: QWidget
    key_container: QWidget
    key_input: QLineEdit
    key_apply_button: QWidget
    model_combo: QComboBox
    status_label: QWidget


class ConfigPage(QWidget):
    message = pyqtSignal(str)

    CATEGORIES = ("llm", "vlm", "embedding")

    def __init__(self, service, parent: QWidget | None = None, theme_manager=None):
        super().__init__(parent)
        self.service = service
        self.theme_manager = theme_manager
        self._models_cache: list[ModelConfig] = []
        self._loading = True

        # Per-category vendor key overrides (env var value).  When None the
        # shared key from os.environ is used.
        self._key_overrides: dict[str, str | None] = {c: None for c in self.CATEGORIES}

        load_ui("config_page.ui", self)
        self._slots = self._build_slots()
        self._setup_ui()
        self._load_state()
        self._loading = False

    # ------------------------------------------------------------------ #
    #  Widget mapping
    # ------------------------------------------------------------------ #

    def _build_slots(self) -> dict[str, CategorySlot]:
        return {
            "llm": CategorySlot(
                vendor_combo=self.llm_vendor_combo,
                ollama_host_label=self.llmOllamaHostLabel,
                ollama_host_container=self.llm_ollama_host_container,
                ollama_host_input=self.llm_ollama_host_input,
                ollama_verify_button=self.llm_ollama_verify_button,
                key_label=self.llmKeyLabel,
                key_container=self.llm_key_container,
                key_input=self.llm_key_input,
                key_apply_button=self.llm_key_apply_button,
                model_combo=self.llm_combo,
                status_label=self.llm_status_label,
            ),
            "vlm": CategorySlot(
                vendor_combo=self.vlm_vendor_combo,
                ollama_host_label=self.vlmOllamaHostLabel,
                ollama_host_container=self.vlm_ollama_host_container,
                ollama_host_input=self.vlm_ollama_host_input,
                ollama_verify_button=self.vlm_ollama_verify_button,
                key_label=self.vlmKeyLabel,
                key_container=self.vlm_key_container,
                key_input=self.vlm_key_input,
                key_apply_button=self.vlm_key_apply_button,
                model_combo=self.vlm_combo,
                status_label=self.vlm_status_label,
            ),
            "embedding": CategorySlot(
                vendor_combo=self.embedding_vendor_combo,
                ollama_host_label=self.embeddingOllamaHostLabel,
                ollama_host_container=self.embedding_ollama_host_container,
                ollama_host_input=self.embedding_ollama_host_input,
                ollama_verify_button=self.embedding_ollama_verify_button,
                key_label=self.embeddingKeyLabel,
                key_container=self.embedding_key_container,
                key_input=self.embedding_key_input,
                key_apply_button=self.embedding_key_apply_button,
                model_combo=self.embedding_combo,
                status_label=self.embedding_status_label,
            ),
        }

    # ------------------------------------------------------------------ #
    #  Setup
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        self.debugLabel.setText("Modo Debug")

        # General controls
        self.debug_check.toggled.connect(self._set_debug)
        for value in EvaluationMode:
            self.eval_mode_combo.addItem(self._evaluation_label(value), value)
        self.eval_mode_combo.currentIndexChanged.connect(self._set_evaluation_mode)
        for value in RealEvaluation:
            self.real_eval_combo.addItem(self._real_evaluation_label(value), value)
        self.real_eval_combo.currentIndexChanged.connect(self._set_real_evaluation)

        # Theme combo
        self.theme_combo = QComboBox(self)
        self.theme_combo.addItem("Claro", "light")
        self.theme_combo.addItem("Oscuro", "dark")
        self.theme_combo.currentIndexChanged.connect(self._theme_changed)
        self.generalForm.addRow("Tema visual", self.theme_combo)
        self.update_theme_ui()

        # Tab titles
        self.category_tabs.setTabText(0, "LLM")
        self.category_tabs.setTabText(1, "VLM")
        self.category_tabs.setTabText(2, "Embeddings")

        # Per-category setup
        for cat in self.CATEGORIES:
            slot = self._slots[cat]

            # Populate vendor combo
            for provider in LlmProvider:
                slot.vendor_combo.addItem(provider.value.capitalize(), provider)
            slot.vendor_combo.currentIndexChanged.connect(
                lambda _idx, c=cat: self._vendor_changed(c)
            )

            # Ollama host defaults
            slot.ollama_host_input.setPlaceholderText("localhost")
            slot.ollama_verify_button.clicked.connect(
                lambda _checked, c=cat: self._verify_ollama(c)
            )

            # API key
            slot.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            slot.key_input.setPlaceholderText("API key")
            slot.key_apply_button.clicked.connect(
                lambda _checked, c=cat: self._apply_key(c)
            )

            # Model combo
            slot.model_combo.currentIndexChanged.connect(
                lambda _idx, c=cat: self._set_model(c)
            )

            # Tooltips
            slot.vendor_combo.setToolTip("Proveedor de modelos para esta categoría.")
            slot.ollama_host_input.setToolTip("Host o IP de Ollama.")
            slot.ollama_verify_button.setToolTip("Verifica conexión y actualiza catálogo.")
            slot.key_input.setToolTip("Clave de API para esta sesión.")
            slot.key_apply_button.setToolTip("Carga la clave en memoria.")
            slot.model_combo.setToolTip("Modelo activo para esta categoría.")

    # ------------------------------------------------------------------ #
    #  State load
    # ------------------------------------------------------------------ #

    def _load_state(self) -> None:
        self.debug_check.setChecked(self.service.debug_mode)
        self._select_data(self.eval_mode_combo, self.service.evaluation_mode)
        self._select_data(self.real_eval_combo, self.service.real_evaluation)

        # Per-category: select vendor based on active model's provider
        config_map = {
            "llm": self.service.model_provider._llm_config,
            "vlm": self.service.model_provider._vlm_config,
            "embedding": self.service.model_provider._embedding_config,
        }
        for cat in self.CATEGORIES:
            slot = self._slots[cat]
            cfg = config_map[cat]
            provider = cfg.provider if cfg and cfg.is_configured() else LlmProvider.GEMINI
            self._select_data(slot.vendor_combo, provider)
            slot.ollama_host_input.setText(
                getattr(self.service.model_provider, "_local_ip", "localhost")
            )
            self._sync_vendor_controls(cat)
            self._update_key_placeholder(cat)
            self._refresh_models(cat)

    # ------------------------------------------------------------------ #
    #  Vendor change / controls sync
    # ------------------------------------------------------------------ #

    def _vendor_changed(self, category: str) -> None:
        if not self._loading:
            self._sync_vendor_controls(category)
            self._refresh_models(category)

    def _sync_vendor_controls(self, category: str) -> None:
        slot = self._slots[category]
        provider = slot.vendor_combo.currentData()
        is_ollama = provider == LlmProvider.OLLAMA

        slot.ollama_host_label.setVisible(is_ollama)
        slot.ollama_host_container.setVisible(is_ollama)
        slot.key_label.setVisible(not is_ollama)
        slot.key_container.setVisible(not is_ollama)

        if not is_ollama:
            self._update_key_placeholder(category)
        self._update_status_label(category)

    # ------------------------------------------------------------------ #
    #  Ollama verification
    # ------------------------------------------------------------------ #

    def _verify_ollama(self, category: str) -> None:
        slot = self._slots[category]
        host = slot.ollama_host_input.text().strip() or "localhost"
        try:
            self.service.model_provider.set_ollama_ip(host)
            self.service.model_provider.refresh_catalog(LlmProvider.OLLAMA)
            self._refresh_models(category)
            if self.service.model_provider.is_ollama_reachable:
                self.message.emit(f"Ollama disponible en {host}. Catálogo actualizado.")
            else:
                self.message.emit(f"Ollama no disponible en {host}.")
        except Exception as error:
            self._show_messagebox("critical", "No se pudo verificar Ollama", str(error))
        finally:
            self._update_status_label(category)

    # ------------------------------------------------------------------ #
    #  API key management
    # ------------------------------------------------------------------ #

    def _apply_key(self, category: str) -> None:
        slot = self._slots[category]
        provider = slot.vendor_combo.currentData()
        env_key = self._provider_env_key(provider)
        api_key = slot.key_input.text().strip()

        if not api_key:
            self._show_messagebox(
                "warning",
                "Credencial requerida",
                f"Ingresa {env_key} para usar modelos {self._provider_display(provider)}.",
            )
            self._update_status_label(category)
            return

        is_valid, validation_message = self.service.model_provider.validate_provider_credentials(
            provider,
            api_key,
        )
        if not is_valid:
            self._show_messagebox("warning", "Credencial inválida", validation_message)
            self._update_status_label(category)
            return

        os.environ[env_key] = api_key
        self._key_overrides[category] = api_key
        slot.key_input.clear()
        self._update_key_placeholder(category)
        self.service.model_provider.refresh_catalog(provider)
        self._refresh_models(category)
        self.message.emit(
            f"Credencial {self._provider_display(provider)} validada y cargada para {category.upper()}."
        )

    def _update_key_placeholder(self, category: str) -> None:
        slot = self._slots[category]
        provider = slot.vendor_combo.currentData()
        env_key = self._provider_env_key(provider)
        override = self._key_overrides.get(category)
        if override:
            slot.key_input.setPlaceholderText(f"{env_key} (override cargada)")
        elif os.environ.get(env_key):
            slot.key_input.setPlaceholderText(f"{env_key} cargada en sesión")
        else:
            slot.key_input.setPlaceholderText(env_key)
        slot.key_label.setText(f"Credencial {self._provider_display(provider)}")

    # ------------------------------------------------------------------ #
    #  Model refresh (per category)
    # ------------------------------------------------------------------ #

    def _refresh_models(self, category: str) -> None:
        slot = self._slots[category]
        all_models = self._safe_operation(
            self.service.model_provider.list_models, "Modelos no disponibles"
        ) or []
        self._models_cache = all_models

        # Map category to ModelProvider config for current selection
        config_map = {
            "llm": self.service.model_provider._llm_config,
            "vlm": self.service.model_provider._llm_config,
            "embedding": self.service.model_provider._embedding_config,
        }
        category_type = {"llm": "chat", "vlm": "chat", "embedding": "embedding"}[category]
        current_config = config_map[category]
        current_id = current_config.model_id if current_config and current_config.is_configured() else None

        items = [("Sin configurar", None)]
        selected_vendor = slot.vendor_combo.currentData()
        for model in all_models:
            if model.category == category_type and model.provider == selected_vendor:
                label = f"{self._provider_display(model.provider)} - {model.model_id}"
                items.append((label, model))

        current_model = None
        if current_config and current_config.is_configured():
            for _label, data in items:
                if data and data.model_id == current_id and data.provider == current_config.provider:
                    current_model = data
                    break

        self._populate_combo(slot.model_combo, items, current_model)
        self._update_status_label(category)

    # ------------------------------------------------------------------ #
    #  Model activation
    # ------------------------------------------------------------------ #

    def _set_model(self, category: str) -> None:
        if self._loading:
            return
        slot = self._slots[category]
        model = slot.model_combo.currentData()
        if model is None:
            return
        if not self._can_activate_model(model, category):
            return
        try:
            setter_map = {
                "llm": self.service.model_provider.set_llm,
                "vlm": self.service.model_provider.set_vlm,
                "embedding": self.service.model_provider.set_embedding,
            }
            setter_map[category](model)

            # Side effects
            if category == "llm":
                self.service.update_evaluator_llm()
            elif category in ("vlm", "embedding"):
                self.service.reset_requirements_extractor()

            self._update_status_label(category)
            self._update_active_models_label()
            self.message.emit(
                f"{category.upper()} activo: {self._provider_display(model.provider)} / {model.model_id}"
            )
        except Exception as error:
            self._show_messagebox("critical", "No se pudo configurar", str(error))

    # ------------------------------------------------------------------ #
    #  Validation
    # ------------------------------------------------------------------ #

    def _can_activate_model(self, model: ModelConfig, category: str) -> bool:
        # Claude not supported for embedding / vlm
        if model.provider == LlmProvider.CLAUDE and model.category in {"embedding", "vlm"}:
            self._show_messagebox(
                "warning",
                "Categoría no soportada",
                "Claude se puede usar como LLM. Para embeddings o VLM usa OpenAI, Gemini u Ollama.",
            )
            self._refresh_models(category)
            return False

        # Cloud providers need credentials
        if model.provider != LlmProvider.OLLAMA:
            env_key = self._provider_env_key(model.provider)
            # Check if this category has an override or the env var is set
            override = self._key_overrides.get(category)
            has_key = bool(override or os.environ.get(env_key))
            if not has_key:
                self._show_messagebox(
                    "warning",
                    "Credencial requerida",
                    f"Carga {env_key} antes de activar modelos {self._provider_display(model.provider)}.",
                )
                self._refresh_models(category)
                return False

        # Ollama needs to be reachable
        if model.provider == LlmProvider.OLLAMA and not self.service.model_provider.is_ollama_reachable:
            self._show_messagebox(
                "warning",
                "Vendor no disponible",
                "Verifica la conexión con Ollama antes de activar modelos locales.",
            )
            self._refresh_models(category)
            return False

        return True

    # ------------------------------------------------------------------ #
    #  Status labels
    # ------------------------------------------------------------------ #

    def _update_status_label(self, category: str) -> None:
        slot = self._slots[category]
        provider = slot.vendor_combo.currentData()
        ollama_reachable = self.service.model_provider.is_ollama_reachable

        if provider == LlmProvider.OLLAMA:
            host = slot.ollama_host_input.text().strip() or "localhost"
            status = (
                f"Ollama disponible en {host}"
                if ollama_reachable
                else f"Ollama no disponible en {host}"
            )
        else:
            env_key = self._provider_env_key(provider)
            provider_name = self._provider_display(provider)
            override = self._key_overrides.get(category)
            ready = bool(override or os.environ.get(env_key))
            status = (
                ""
                if ready
                else f"{provider_name} requiere {env_key}"
            )

        slot.status_label.setText(status)

    def _update_active_models_label(self) -> None:
        parts = []
        for cat, display in [("llm", "LLM"), ("vlm", "VLM"), ("embedding", "Embeddings")]:
            cfg = getattr(self.service.model_provider, f"_{cat}_config", None)
            parts.append(self._active_category_label(display, cfg))
        self.active_models_label.setText("Modelos activos - " + " | ".join(parts))

    def _active_category_label(self, name: str, config) -> str:
        if not config or not config.is_configured():
            return f"{name}: sin configurar"
        return f"{name}: {self._provider_display(config.provider)} / {config.model_id}"

    # ------------------------------------------------------------------ #
    #  General settings
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def set_compact(self, compact: bool) -> None:
        policy = (
            QFormLayout.RowWrapPolicy.WrapAllRows
            if compact
            else QFormLayout.RowWrapPolicy.DontWrapRows
        )
        self.generalForm.setRowWrapPolicy(policy)
        for cat in self.CATEGORIES:
            form = self._slots[cat].model_combo.parent().findChild(QFormLayout)
            if form:
                form.setRowWrapPolicy(policy)

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

    @staticmethod
    def _evaluation_label(value: EvaluationMode) -> str:
        return "Agente con recuperación semántica" if value == EvaluationMode.AGENT_AI else "Pipeline LLM"

    @staticmethod
    def _real_evaluation_label(value: RealEvaluation) -> str:
        return "Cumplido" if value == RealEvaluation.FULFILLED else "No cumplido"

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
