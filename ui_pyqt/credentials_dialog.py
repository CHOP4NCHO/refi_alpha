"""Session-only API key loader for cloud providers."""

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.enums import LlmProvider


class CredentialsDialog(QDialog):
    """Modal dialog to load cloud API keys into the current process session."""

    message = pyqtSignal(str)

    _PROVIDERS = [
        (LlmProvider.GEMINI, "GOOGLE_API_KEY", "Gemini"),
        (LlmProvider.OPENAI, "OPENAI_API_KEY", "OpenAI"),
        (LlmProvider.CLAUDE, "ANTHROPIC_API_KEY", "Claude"),
    ]

    def __init__(self, service, theme_manager=None, parent=None):
        super().__init__(parent)

        self.service = service
        self.theme_manager = theme_manager

        self._key_inputs: dict[LlmProvider, QLineEdit] = {}
        self._status_labels: dict[LlmProvider, QLabel] = {}
        self._message_label: QLabel | None = None

        self.setWindowTitle("Cargar credenciales")

        # Evita que el diálogo cambie de tamaño cuando aparecen mensajes.
        self.setFixedSize(760, 410)

        self._build_ui()

        # Cualquier emisión de `message` se muestra en el área reservada.
        self.message.connect(self._show_message)

        if self.theme_manager:
            self.theme_manager.apply_to(self)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Credenciales de proveedores")
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        notice = QLabel(
            "Las API keys solo estarán disponibles durante esta sesión."
        )
        notice.setObjectName("credentialsNotice")
        notice.setWordWrap(True)
        root.addWidget(notice)

        card = QFrame()
        card.setProperty("card", True)

        form = QFormLayout(card)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.setContentsMargins(16, 16, 16, 16)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )

        for provider, env_key, display in self._PROVIDERS:
            provider_label = QLabel(display)
            provider_label.setStyleSheet("font-weight: 600;")

            form.addRow(
                provider_label,
                self._build_provider_row(provider, env_key),
            )

        root.addWidget(card)

        # El espacio existe siempre, incluso cuando no hay texto.
        message_frame = QFrame()
        message_frame.setObjectName("credentialsMessageFrame")
        message_frame.setProperty("card", True)
        message_frame.setFixedHeight(58)
        message_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        message_layout = QVBoxLayout(message_frame)
        message_layout.setContentsMargins(12, 8, 12, 8)
        message_layout.setSpacing(0)

        self._message_label = QLabel("")
        self._message_label.setObjectName("credentialsMessage")
        self._message_label.setProperty("messageType", "empty")
        self._message_label.setWordWrap(True)
        self._message_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )
        self._message_label.setMinimumHeight(40)
        self._message_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        message_layout.addWidget(self._message_label)
        root.addWidget(message_frame)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _build_provider_row(
        self,
        provider: LlmProvider,
        env_key: str,
    ) -> QWidget:
        row = QWidget()

        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        key_input = QLineEdit()
        key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_input.setMinimumWidth(300)
        key_input.setPlaceholderText(
            f"{env_key} cargada en sesión"
            if os.environ.get(env_key)
            else env_key
        )

        load_button = QPushButton("Cargar")
        load_button.setCursor(Qt.CursorShape.PointingHandCursor)
        load_button.setFixedWidth(82)
        load_button.clicked.connect(
            lambda _checked, p=provider: self._apply_key(p)
        )

        status = QLabel("")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Todos los estados conservan exactamente el mismo ancho.
        status.setFixedWidth(142)
        status.setMinimumHeight(34)

        status.setProperty("muted", True)
        status.setProperty("credentialStatus", "empty")

        if os.environ.get(env_key):
            self._mark_loaded(status, "Cargada en sesión")

        self._key_inputs[provider] = key_input
        self._status_labels[provider] = status

        layout.addWidget(key_input, 1)
        layout.addWidget(load_button)
        layout.addWidget(status)

        return row

    def _apply_key(self, provider: LlmProvider) -> None:
        env_key = self._provider_env_key(provider)
        display = self._provider_display(provider)

        key_input = self._key_inputs[provider]
        api_key = key_input.text().strip()

        if not api_key:
            error_message = (
                f"Ingresa {env_key} para usar modelos {display}."
            )
            self._show_message(error_message, "error")

            QMessageBox.warning(
                self,
                "Credencial requerida",
                error_message,
            )
            return

        self._show_message(
            f"Validando credencial de {display}...",
            "info",
        )

        is_valid, validation_message = (
            self.service.model_provider.validate_provider_credentials(
                provider,
                api_key,
            )
        )

        if not is_valid:
            self._mark_unavailable(
                self._status_labels[provider],
                "No disponible",
            )

            self._show_message(
                validation_message,
                "error",
            )

            QMessageBox.warning(
                self,
                "Credencial inválida",
                validation_message,
            )
            return

        os.environ[env_key] = api_key
        self.service.model_provider.refresh_catalog(provider)

        key_input.clear()
        key_input.setPlaceholderText(
            f"{env_key} cargada en sesión"
        )

        self._mark_available(
            self._status_labels[provider],
            "Disponible",
        )

        self.message.emit(
            f"Credencial de {display} cargada para esta sesión."
        )

    def _show_message(
        self,
        text: str,
        message_type: str = "success",
    ) -> None:
        """Display a message without changing the dialog geometry."""

        if self._message_label is None:
            return

        self._message_label.setText(text)
        self._message_label.setProperty(
            "messageType",
            message_type,
        )

        self._refresh_style(self._message_label)

    def _clear_message(self) -> None:
        """Clear the message while preserving its reserved space."""

        if self._message_label is None:
            return

        self._message_label.setText("")
        self._message_label.setProperty(
            "messageType",
            "empty",
        )

        self._refresh_style(self._message_label)

    def _mark_loaded(
        self,
        status_label: QLabel,
        text: str,
    ) -> None:
        status_label.setText(text)
        status_label.setProperty("muted", False)
        status_label.setProperty(
            "credentialStatus",
            "loaded",
        )
        self._refresh_style(status_label)

    def _mark_available(
        self,
        status_label: QLabel,
        text: str,
    ) -> None:
        status_label.setText(text)
        status_label.setProperty("muted", False)
        status_label.setProperty(
            "credentialStatus",
            "available",
        )
        self._refresh_style(status_label)

    def _mark_unavailable(
        self,
        status_label: QLabel,
        text: str,
    ) -> None:
        status_label.setText(text)
        status_label.setProperty("muted", False)
        status_label.setProperty(
            "credentialStatus",
            "unavailable",
        )
        self._refresh_style(status_label)

    @staticmethod
    def _refresh_style(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    @staticmethod
    def _provider_env_key(
        provider: LlmProvider | None,
    ) -> str:
        env_keys = {
            LlmProvider.GEMINI: "GOOGLE_API_KEY",
            LlmProvider.OPENAI: "OPENAI_API_KEY",
            LlmProvider.CLAUDE: "ANTHROPIC_API_KEY",
        }
        return env_keys.get(provider, "API_KEY")

    @staticmethod
    def _provider_display(
        provider: LlmProvider | None,
    ) -> str:
        names = {
            LlmProvider.GEMINI: "Gemini",
            LlmProvider.OPENAI: "OpenAI",
            LlmProvider.CLAUDE: "Claude",
            LlmProvider.OLLAMA: "Ollama",
        }
        return names.get(provider, "Proveedor")