import logging
import os

from langchain_ollama import ChatOllama
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from pydantic import AnyUrl
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions, ResponseFormat

from .enums import LlmProvider
from .model_config import ModelConfig
from .exceptions import ModelConfigurationError

logger = logging.getLogger(__name__)


class ModelFactory:
    """Builds executable LangChain / Docling objects from ModelConfig."""

    def __init__(self, local_ip: str = "localhost", cloud_ip: str = "", temperature: float = 0.1):
        self._local_ip = local_ip
        self._cloud_ip = cloud_ip
        self._temperature = temperature

    def set_local_ip(self, ip: str) -> None:
        self._local_ip = ip

    def create_llm(self, config: ModelConfig, operation: str | None = None):
        if not config.is_configured():
            raise ModelConfigurationError("llm", operation or "general")

        if config.provider == LlmProvider.OLLAMA:
            return ChatOllama(
                model=config.model_id or " ",
                base_url=f"http://{self._local_ip}:11434",
                temperature=self._temperature,
                format="json",
            )

        if config.provider in (LlmProvider.GEMINI, LlmProvider.OPENAI, LlmProvider.CLAUDE):
            return init_chat_model(
                config.model_id,
                temperature=self._temperature,
            )

        raise ValueError(
            f"Proveedor LLM '{config.provider.value if config.provider else 'None'}' no soportado."
        )

    def create_embeddings(self, config: ModelConfig, operation: str | None = None):
        if not config.is_configured():
            raise ModelConfigurationError("embedding", operation or "general")

        if config.provider == LlmProvider.OLLAMA:
            return init_embeddings(
                f"ollama:{config.model_id}",
                base_url=f"http://{self._local_ip}:11434",
            )

        if config.provider in (LlmProvider.GEMINI, LlmProvider.OPENAI):
            return init_embeddings(config.model_id or " ")

        raise ValueError(
            f"Proveedor embeddings '{config.provider.value if config.provider else 'None'}' no soportado. "
            f"Claude no ofrece embeddings compatibles."
        )

    def create_vlm_options(self, config: ModelConfig, prompt: str = "OCR the full page to markdown", operation: str | None = None) -> ApiVlmOptions:
        if not config.is_configured():
            raise ModelConfigurationError("vlm", operation or "general")

        if config.provider == LlmProvider.OLLAMA:
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

        if config.provider == LlmProvider.GEMINI:
            api_key = os.environ.get("GOOGLE_API_KEY", "")
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            trimmed_id = config.model_id.replace("google_genai:","")
            trimmed_id = trimmed_id.replace("models/","")
            return ApiVlmOptions(
                url=AnyUrl("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"),
                headers=headers,
                params=dict(model=trimmed_id),
                prompt=prompt,
                timeout=90,
                scale=1.0,
                response_format=ResponseFormat.MARKDOWN,
            )

        raise ValueError(
            f"Proveedor VLM '{config.provider.value if config.provider else 'None'}' no soportado. "
            f"Claude no es compatible con el flujo VLM actual."
        )
