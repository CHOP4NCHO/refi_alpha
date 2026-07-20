import os
import requests
from typing import List

from langchain_ollama import ChatOllama
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from pydantic import AnyUrl
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions, ResponseFormat

from .enums import LlmProvider
from .model_config import ModelConfig
from .exceptions import ModelConfigurationError, ModelsNotConfiguredError


class ModelProvider:
    # Constantes para identificar operaciones
    OP_EVALUATE_PIPELINE = "evaluar_pipeline"
    OP_EVALUATE_AGENT = "evaluar_agente"
    OP_IMPORT_PDF = "importar_pdf"

    def __init__(
        self,
        local_ip: str = "localhost",
        cloud_ip: str = "",
        default_llm: ModelConfig | None = None,
        default_embedding: ModelConfig | None = None,
        default_vlm: ModelConfig | None = None,
        fallback_llm: ModelConfig | None = None,
        fallback_embedding: ModelConfig | None = None,
        temperature: float = 0.1,
    ):
        self._local_ip = local_ip
        self._cloud_ip = cloud_ip

        self._llm_config = default_llm or ModelConfig(None, None)
        self._embedding_config = default_embedding or ModelConfig(None, None)
        self._vlm_config = default_vlm or ModelConfig(None, None)

        self._fallback_llm = fallback_llm
        self._fallback_embedding = fallback_embedding

        self._temperature = temperature

        self.is_ollama_reachable = self._check_connection(self._local_ip)

    # --------------------------------------------------
    # Connection
    # --------------------------------------------------

    def _check_connection(self, ip: str) -> bool:
        try:
            response = requests.get(f"http://{ip}:11434/api/tags", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

    # Métodos de consulta (retornan bool, no lanzan excepciones)
    def is_llm_configured(self) -> bool:
        return self._llm_config is not None and self._llm_config.is_configured()

    def is_embedding_configured(self) -> bool:
        return self._embedding_config is not None and self._embedding_config.is_configured()

    def is_vlm_configured(self) -> bool:
        return self._vlm_config is not None and self._vlm_config.is_configured()

    # --------------------------------------------------
    # Validación contextual por operación
    # --------------------------------------------------

    def validate_for_pipeline(self) -> None:
        """Valida modelos requeridos para evaluación en modo Pipeline."""
        missing = []
        if not self.is_llm_configured():
            missing.append("LLM")
        if missing:
            raise ModelsNotConfiguredError(missing, self.OP_EVALUATE_PIPELINE)

    def validate_for_agent(self) -> None:
        """Valida modelos requeridos para evaluación en modo Agente."""
        missing = []
        if not self.is_llm_configured():
            missing.append("LLM")
        if not self.is_embedding_configured():
            missing.append("Embedding")
        if missing:
            raise ModelsNotConfiguredError(missing, self.OP_EVALUATE_AGENT)

    def validate_for_pdf_import(self) -> None:
        """Valida modelos requeridos para importar PDF."""
        missing = []
        if not self.is_vlm_configured():
            missing.append("VLM")
        if missing:
            raise ModelsNotConfiguredError(missing, self.OP_IMPORT_PDF)

    def validate_for_operation(self, operation: str) -> None:
        """Valida modelos para una operación específica."""
        validators = {
            self.OP_EVALUATE_PIPELINE: self.validate_for_pipeline,
            self.OP_EVALUATE_AGENT: self.validate_for_agent,
            self.OP_IMPORT_PDF: self.validate_for_pdf_import,
        }
        
        validator = validators.get(operation)
        if validator:
            validator()
        else:
            raise ValueError(f"Operación desconocida: {operation}")

    # --------------------------------------------------
    # LLM
    # --------------------------------------------------

    def get_llm(self, operation: str | None = None):
        """ Returns current LLM Reference"""
        if not self.is_llm_configured():
            raise ModelConfigurationError("llm", operation or "general")
        config = self._llm_config

        if config.provider == LlmProvider.OLLAMA and self.is_ollama_reachable:
            return ChatOllama(
                model=config.model_id or " ",
                base_url=f"http://{self._local_ip}:11434",
                temperature=self._temperature,
                format="json"
            )

        if config.provider in (LlmProvider.GEMINI, LlmProvider.OPENAI, LlmProvider.CLAUDE):
            return init_chat_model(
                config.model_id,
                temperature=self._temperature
            )

        # Fallback: Ollama unreachable, use cloud model
        if self._fallback_llm and self._fallback_llm.is_configured():
            return init_chat_model(
                self._fallback_llm.model_id,
                temperature=self._temperature
            )

        raise ValueError(
            f"Proveedor '{config.provider.value if config.provider else 'None'}' no disponible "
            f"(Ollama reachable={self.is_ollama_reachable}). "
            f"Configura un modelo fallback en CONFIG."
        )

    def get_llm_label(self) -> str:
        """
        Returns a readable identifier of the active model.
        Example: 'ollama:llama3' or 'gemini:gemini-2.5-flash'
        """
        provider_name = self._llm_config.provider.value if (self._llm_config and self._llm_config.provider) else "None"
        model_id = self._llm_config.model_id if (self._llm_config and self._llm_config.model_id) else "None"
        return f"{provider_name}:{model_id}"

    # --------------------------------------------------
    # Embeddings
    # --------------------------------------------------

    def get_embeddings(self, operation: str | None = None):
        if not self.is_embedding_configured():
            raise ModelConfigurationError("embedding", operation or "general")
        config = self._embedding_config

        if config.provider == LlmProvider.OLLAMA and self.is_ollama_reachable:
            return init_embeddings(
                f"ollama:{config.model_id}",
                base_url=f"http://{self._local_ip}:11434"
            )

        if config.provider in (LlmProvider.GEMINI, LlmProvider.OPENAI):
            return init_embeddings(config.model_id or " ")

        # Fallback: Ollama unreachable, use cloud embeddings
        if self._fallback_embedding and self._fallback_embedding.is_configured():
            return init_embeddings(self._fallback_embedding.model_id or " ")

        raise ValueError(
            f"Proveedor embeddings '{config.provider.value if config.provider else 'None'}' no disponible "
            f"(Ollama reachable={self.is_ollama_reachable}). "
            f"Configura un modelo fallback en CONFIG."
        )

    # --------------------------------------------------
    # VLM (Docling)
    # --------------------------------------------------

    def get_vlm_options(self, prompt: str = "OCR the full page to markdown", operation: str | None = None) -> ApiVlmOptions:
        if not self.is_vlm_configured():
            raise ModelConfigurationError("vlm", operation or "general")
        config = self._vlm_config

        if config.provider == LlmProvider.OLLAMA and self.is_ollama_reachable:
            return ApiVlmOptions(
                url=AnyUrl(f"http://{self._local_ip}:11434/v1/chat/completions"),
                params=dict(model=config.model_id),
                prompt=prompt,
                timeout=90,
                scale=1.0,
                response_format=ResponseFormat.MARKDOWN,
            )

        if config.provider == LlmProvider.OPENAI:
            api_key = os.environ.get("OPENAI_API_KEY", "")
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            return ApiVlmOptions(
                url=AnyUrl("https://api.openai.com/v1/chat/completions"),
                headers=headers,
                params=dict(model=config.model_id),
                prompt=prompt,
                timeout=90,
                scale=1.0,
                response_format=ResponseFormat.MARKDOWN,
            )

        api_key = os.environ.get("GOOGLE_API_KEY", "")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

        return ApiVlmOptions(
            url=AnyUrl(f"https://{self._cloud_ip}/chat/completions"),
            headers=headers,
            params=dict(model=config.model_id),
            prompt=prompt,
            timeout=90,
            scale=1.0,
            response_format=ResponseFormat.MARKDOWN,
        )

    # --------------------------------------------------
    # Setters
    # --------------------------------------------------

    def set_llm(self, config: ModelConfig):
        self._llm_config = config

    def set_embedding(self, config: ModelConfig):
        self._embedding_config = config

    def set_vlm(self, config: ModelConfig):
        self._vlm_config = config

    # --------------------------------------------------
    # Model discovery
    # TODO: mejorar el import automático de Model Config según el LlmProvider
    # --------------------------------------------------

    def list_models(self) -> List[ModelConfig]:
        models: List[ModelConfig] = []

        # Ollama (dynamic)
        if self.is_ollama_reachable:
            try:
                response = requests.get(f"http://{self._local_ip}:11434/api/tags")
                data = response.json()

                for m in data.get("models", []):
                    model_id = m["name"]
                    models.append(ModelConfig(
                        provider=LlmProvider.OLLAMA,
                        model_id=model_id,
                        category=self._classify_ollama_model(model_id)
                    ))
            except Exception:
                pass

        # Cloud providers (static catalogs)
        models.extend([
            ModelConfig(LlmProvider.GEMINI, "google_genai:gemini-3.1-flash-lite", "chat"),
            ModelConfig(LlmProvider.GEMINI, "google_genai:gemini-2.5-flash", "chat"),
            ModelConfig(LlmProvider.GEMINI, "google_genai:gemini-2.5-pro", "chat"),
            ModelConfig(LlmProvider.GEMINI, "gemini-2.5-flash-lite", "vlm"),
            ModelConfig(LlmProvider.GEMINI, "google_genai:gemini-embedding-2", "embedding"),
            ModelConfig(LlmProvider.OPENAI, "openai:gpt-5.1", "chat"),
            ModelConfig(LlmProvider.OPENAI, "openai:gpt-5-mini", "chat"),
            ModelConfig(LlmProvider.OPENAI, "openai:gpt-4.1-mini", "chat"),
            ModelConfig(LlmProvider.OPENAI, "gpt-4o-mini", "vlm"),
            ModelConfig(LlmProvider.OPENAI, "gpt-4o", "vlm"),
            ModelConfig(LlmProvider.OPENAI, "openai:text-embedding-3-small", "embedding"),
            ModelConfig(LlmProvider.OPENAI, "openai:text-embedding-3-large", "embedding"),
            ModelConfig(LlmProvider.CLAUDE, "anthropic:claude-opus-4-7", "chat"),
            ModelConfig(LlmProvider.CLAUDE, "anthropic:claude-sonnet-4-6", "chat"),
            ModelConfig(LlmProvider.CLAUDE, "anthropic:claude-haiku-4-5", "chat"),
        ])

        return models

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @property
    def current_llm(self) -> str:
        return self._llm_config.model_id if (self._llm_config and self._llm_config.model_id) else ""

    @property
    def current_vlm(self) -> str:
        return self._vlm_config.model_id if (self._vlm_config and self._vlm_config.model_id) else ""

    @property
    def current_embedding(self) -> str:
        return self._embedding_config.model_id if (self._embedding_config and self._embedding_config.model_id) else ""

    @property
    def current_provider(self) -> LlmProvider | None:
        return self._llm_config.provider if self._llm_config else None

    def is_local_provider(self) -> bool:
        """Returns True if the active model is using a local provider (Ollama)."""
        return (
            self._llm_config is not None
            and self._llm_config.provider == LlmProvider.OLLAMA
            and self.is_ollama_reachable
        )

    def set_ollama_ip(self, ip: str) -> None:
        """Update the Ollama IP and re-verify the connection."""
        self._local_ip = ip
        self.is_ollama_reachable = self._check_connection(ip)

    @staticmethod
    def _classify_ollama_model(model_id: str) -> str:
        normalized = model_id.lower()
        embedding_markers = (
            "embed",
            "embedding",
            "nomic-embed",
            "mxbai-embed",
            "bge-",
            "e5-",
            "snowflake-arctic-embed",
        )
        vlm_markers = (
            "vision",
            "llava",
            "bakllava",
            "minicpm-v",
            "moondream",
            "granite3.2-vision",
            "gemma3",
        )
        if any(marker in normalized for marker in embedding_markers):
            return "embedding"
        if any(marker in normalized for marker in vlm_markers):
            return "vlm"
        return "chat"
