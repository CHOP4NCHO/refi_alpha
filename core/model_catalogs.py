import logging
import os
from typing import Literal

import requests

from .enums import LlmProvider
from .model_config import ModelConfig

logger = logging.getLogger(__name__)


class ProviderCatalog:
    """Base class responsible for listing and classifying models of a provider."""

    provider: LlmProvider

    def __init__(self, provider: LlmProvider):
        self.provider = provider
        self._cache: list[ModelConfig] | None = None
        self._last_error: str | None = None
        self._source: Literal["remote", "static", "empty"] = "empty"

    def list_models(self) -> list[ModelConfig]:
        if self._cache is not None:
            return list(self._cache)
        self.refresh()
        return list(self._cache or [])

    def refresh(self) -> None:
        raise NotImplementedError

    def get_status(self) -> str:
        if self._source == "remote":
            return "Catálogo remoto cargado"
        if self._source == "static":
            return "Usando fallback estático"
        return "Sin modelos disponibles"

    @property
    def last_error(self) -> str | None:
        return self._last_error


class OllamaCatalog(ProviderCatalog):
    """Discovers models from a local Ollama instance via /api/tags."""

    def __init__(self, local_ip: str = "localhost"):
        super().__init__(LlmProvider.OLLAMA)
        self._local_ip = local_ip

    def set_local_ip(self, ip: str) -> None:
        self._local_ip = ip
        self._cache = None
        self._source = "empty"
        self._last_error = None

    def refresh(self) -> None:
        self._cache = []
        self._last_error = None
        url = f"http://{self._local_ip}:11434/api/tags"
        try:
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            data = response.json()
            for m in data.get("models", []):
                model_id = m["name"]
                category = self._classify(model_id)
                self._cache.append(
                    ModelConfig(
                        provider=LlmProvider.OLLAMA,
                        model_id=model_id,
                        category=category,
                    )
                )
            self._source = "remote"
        except Exception as exc:
            logger.debug("Ollama catalog fetch failed: %s", exc)
            self._last_error = str(exc)
            self._source = "static"

    @staticmethod
    def _classify(model_id: str) -> str:
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


class OpenAICatalog(ProviderCatalog):
    """Lists OpenAI models via the REST API, with static fallback."""

    STATIC_MODELS: list[ModelConfig] = [
        ModelConfig(LlmProvider.OPENAI, "openai:gpt-5.1", "chat"),
        ModelConfig(LlmProvider.OPENAI, "openai:gpt-5-mini", "chat"),
        ModelConfig(LlmProvider.OPENAI, "openai:gpt-4.1-mini", "chat"),
        ModelConfig(LlmProvider.OPENAI, "gpt-4o-mini", "vlm"),
        ModelConfig(LlmProvider.OPENAI, "gpt-4o", "vlm"),
        ModelConfig(LlmProvider.OPENAI, "openai:text-embedding-3-small", "embedding"),
        ModelConfig(LlmProvider.OPENAI, "openai:text-embedding-3-large", "embedding"),
    ]

    def __init__(self):
        super().__init__(LlmProvider.OPENAI)

    def refresh(self) -> None:
        self._last_error = None
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            self._cache = list(self.STATIC_MODELS)
            self._source = "static"
            return

        try:
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            models: list[ModelConfig] = []
            for item in data.get("data", []):
                model_id = item.get("id", "")
                category = self._classify(model_id)
                if category:
                    prefix = "openai:" if not model_id.startswith("openai:") else ""
                    models.append(
                        ModelConfig(
                            provider=LlmProvider.OPENAI,
                            model_id=f"{prefix}{model_id}",
                            category=category,
                        )
                    )
            self._cache = models if models else list(self.STATIC_MODELS)
            self._source = "remote" if models else "static"
        except Exception as exc:
            logger.debug("OpenAI catalog fetch failed: %s", exc)
            self._last_error = str(exc)
            self._cache = list(self.STATIC_MODELS)
            self._source = "static"

    @staticmethod
    def _classify(model_id: str) -> str | None:
        lower = model_id.lower()
        if lower.startswith("text-embedding"):
            return "embedding"
        if any(kw in lower for kw in ("gpt-4o", "gpt-4.1", "gpt-5")):
            if "mini" in lower:
                return "chat"
            return "chat"
        if lower.startswith("gpt-"):
            return "chat"
        return None


class GeminiCatalog(ProviderCatalog):
    """Lists Google Gemini models, with static fallback."""

    STATIC_MODELS: list[ModelConfig] = [
        ModelConfig(LlmProvider.GEMINI, "google_genai:gemini-3.1-flash-lite", "chat"),
        ModelConfig(LlmProvider.GEMINI, "google_genai:gemini-2.5-flash", "chat"),
        ModelConfig(LlmProvider.GEMINI, "google_genai:gemini-2.5-pro", "chat"),
        ModelConfig(LlmProvider.GEMINI, "gemini-2.5-flash-lite", "vlm"),
        ModelConfig(LlmProvider.GEMINI, "google_genai:gemini-embedding-2", "embedding"),
    ]

    def __init__(self):
        super().__init__(LlmProvider.GEMINI)

    def refresh(self) -> None:
        self._last_error = None
        api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            self._cache = list(self.STATIC_MODELS)
            self._source = "static"
            return

        try:
            response = requests.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            models: list[ModelConfig] = []

            for item in data.get("models", []):
                
                raw_id = item.get("name", "").replace("models/", "")
                category = self._classify(raw_id)
                if category:
                    prefix = "google_genai:" if not raw_id.startswith("google_genai:") else ""
                    models.append(
                        ModelConfig(
                            provider=LlmProvider.GEMINI,
                            model_id=f"{prefix}{raw_id}",
                            category=category,
                        )
                    )

            self._cache = models if models else list(self.STATIC_MODELS)
            self._source = "remote" if models else "static"
        except Exception as exc:
            logger.debug("Gemini catalog fetch failed: %s", exc)
            self._last_error = str(exc)
            self._cache = list(self.STATIC_MODELS)
            self._source = "static"

    @staticmethod
    def _classify(model_id: str) -> str | None:
        lower = model_id.lower()
        #custom classify for LLMs and VLMs
        is_llm = "gemini" in lower and "image" not in lower and "tts" not in lower and "preview" not in lower
        is_vlm = "gemini" in lower
        if "embedding" in lower:
            return "embedding"
        if is_llm:
            return "chat"
        if is_vlm:
            return "vlm"
        return None


class ClaudeCatalog(ProviderCatalog):
    """Lists Anthropic Claude models. No embedding or VLM support."""

    STATIC_MODELS: list[ModelConfig] = [
        ModelConfig(LlmProvider.CLAUDE, "anthropic:claude-opus-4-7", "chat"),
        ModelConfig(LlmProvider.CLAUDE, "anthropic:claude-sonnet-4-6", "chat"),
        ModelConfig(LlmProvider.CLAUDE, "anthropic:claude-haiku-4-5", "chat"),
    ]

    def __init__(self):
        super().__init__(LlmProvider.CLAUDE)

    def refresh(self) -> None:
        self._last_error = None
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            self._cache = list(self.STATIC_MODELS)
            self._source = "static"
            return

        try:
            response = requests.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            models: list[ModelConfig] = []
            for item in data.get("data", []):
                model_id = item.get("id", "")
                if model_id:
                    models.append(
                        ModelConfig(
                            provider=LlmProvider.CLAUDE,
                            model_id=f"anthropic:{model_id}",
                            category="chat",
                        )
                    )
            self._cache = models if models else list(self.STATIC_MODELS)
            self._source = "remote" if models else "static"
        except Exception as exc:
            logger.debug("Claude catalog fetch failed: %s", exc)
            self._last_error = str(exc)
            self._cache = list(self.STATIC_MODELS)
            self._source = "static"
