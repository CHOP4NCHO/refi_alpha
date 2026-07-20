import logging
from typing import List

import requests
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions

from .enums import LlmProvider
from .model_config import ModelConfig
from .exceptions import ModelConfigurationError, ModelsNotConfiguredError
from .model_catalogs import (
    ProviderCatalog,
    OllamaCatalog,
    OpenAICatalog,
    GeminiCatalog,
    ClaudeCatalog,
)
from .model_factory import ModelFactory

logger = logging.getLogger(__name__)


class ModelProvider:
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
        catalogs: dict[LlmProvider, ProviderCatalog] | None = None,
        factory: ModelFactory | None = None,
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

        # Catalogs
        self._catalogs: dict[LlmProvider, ProviderCatalog] = catalogs or {
            LlmProvider.OLLAMA: OllamaCatalog(local_ip),
            LlmProvider.GEMINI: GeminiCatalog(),
            LlmProvider.OPENAI: OpenAICatalog(),
            LlmProvider.CLAUDE: ClaudeCatalog(),
        }

        # Factory
        self._factory = factory or ModelFactory(
            local_ip=local_ip,
            cloud_ip=cloud_ip,
            temperature=temperature,
        )

    # --------------------------------------------------
    # Connection
    # --------------------------------------------------

    def _check_connection(self, ip: str) -> bool:
        try:
            response = requests.get(f"http://{ip}:11434/api/tags", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

    # --------------------------------------------------
    # Query methods (return bool, never raise)
    # --------------------------------------------------

    def is_llm_configured(self) -> bool:
        return self._llm_config is not None and self._llm_config.is_configured()

    def is_embedding_configured(self) -> bool:
        return self._embedding_config is not None and self._embedding_config.is_configured()

    def is_vlm_configured(self) -> bool:
        return self._vlm_config is not None and self._vlm_config.is_configured()

    # --------------------------------------------------
    # Contextual validation per operation
    # --------------------------------------------------

    def validate_for_pipeline(self) -> None:
        missing = []
        if not self.is_llm_configured():
            missing.append("LLM")
        if missing:
            raise ModelsNotConfiguredError(missing, self.OP_EVALUATE_PIPELINE)

    def validate_for_agent(self) -> None:
        missing = []
        if not self.is_llm_configured():
            missing.append("LLM")
        if not self.is_embedding_configured():
            missing.append("Embedding")
        if missing:
            raise ModelsNotConfiguredError(missing, self.OP_EVALUATE_AGENT)

    def validate_for_pdf_import(self) -> None:
        missing = []
        if not self.is_vlm_configured():
            missing.append("VLM")
        if missing:
            raise ModelsNotConfiguredError(missing, self.OP_IMPORT_PDF)

    def validate_for_operation(self, operation: str) -> None:
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
        if not self.is_llm_configured():
            raise ModelConfigurationError("llm", operation or "general")

        config = self._llm_config

        # Try primary config via factory
        if config.provider == LlmProvider.OLLAMA and self.is_ollama_reachable:
            return self._factory.create_llm(config, operation)

        if config.provider in (LlmProvider.GEMINI, LlmProvider.OPENAI, LlmProvider.CLAUDE):
            return self._factory.create_llm(config, operation)

        # Fallback
        if self._fallback_llm and self._fallback_llm.is_configured():
            return self._factory.create_llm(self._fallback_llm, operation)

        raise ValueError(
            f"Proveedor '{config.provider.value if config.provider else 'None'}' no disponible "
            f"(Ollama reachable={self.is_ollama_reachable}). "
            f"Configura un modelo fallback en CONFIG."
        )

    def get_llm_label(self) -> str:
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
            return self._factory.create_embeddings(config, operation)

        if config.provider in (LlmProvider.GEMINI, LlmProvider.OPENAI):
            return self._factory.create_embeddings(config, operation)

        # Fallback
        if self._fallback_embedding and self._fallback_embedding.is_configured():
            return self._factory.create_embeddings(self._fallback_embedding, operation)

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
            return self._factory.create_vlm_options(config, prompt, operation)

        if config.provider in (LlmProvider.OPENAI, LlmProvider.GEMINI):
            return self._factory.create_vlm_options(config, prompt, operation)

        raise ValueError(
            f"Proveedor VLM '{config.provider.value if config.provider else 'None'}' no soportado."
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
    # Catalog refresh
    # --------------------------------------------------

    def refresh_catalog(self, provider: LlmProvider) -> None:
        """Force a catalog to re-fetch models (e.g. after loading an API key)."""
        catalog = self._catalogs.get(provider)
        if catalog is not None:
            catalog._cache = None
            catalog.refresh()

    # --------------------------------------------------
    # Model discovery (union of all catalogs)
    # --------------------------------------------------

    def list_models(self) -> List[ModelConfig]:
        models: List[ModelConfig] = []
        for catalog in self._catalogs.values():
            models.extend(catalog.list_models())
        return self._dedupe_models(models)

    def get_catalog_status(self, provider: LlmProvider) -> str:
        catalog = self._catalogs.get(provider)
        if catalog is None:
            return "Proveedor no registrado"
        return catalog.get_status()

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
        return (
            self._llm_config is not None
            and self._llm_config.provider == LlmProvider.OLLAMA
            and self.is_ollama_reachable
        )

    def set_ollama_ip(self, ip: str) -> None:
        self._local_ip = ip
        self.is_ollama_reachable = self._check_connection(ip)
        self._factory.set_local_ip(ip)
        ollama_catalog = self._catalogs.get(LlmProvider.OLLAMA)
        if isinstance(ollama_catalog, OllamaCatalog):
            ollama_catalog.set_local_ip(ip)

    @staticmethod
    def _dedupe_models(models: list[ModelConfig]) -> list[ModelConfig]:
        seen: set[tuple] = set()
        result: list[ModelConfig] = []
        for m in models:
            key = (m.provider, m.model_id, m.category)
            if key not in seen:
                seen.add(key)
                result.append(m)
        return result
