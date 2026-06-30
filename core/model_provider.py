import os
import requests
from typing import List

from langchain_ollama import ChatOllama
from langchain.chat_models import BaseChatModel, init_chat_model
from langchain.embeddings import init_embeddings
from pydantic import AnyUrl
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions, ResponseFormat

from .enums import LlmProvider
from .model_config import ModelConfig


class ModelProvider:
    def __init__(
        self,
        local_ip: str,
        cloud_ip: str,
        default_llm: ModelConfig,
        default_embedding: ModelConfig,
        default_vlm: ModelConfig,
        temperature: float = 0.1,
    ):
        self._local_ip = local_ip
        self._cloud_ip = cloud_ip

        self._llm_config = default_llm
        self._embedding_config = default_embedding
        self._vlm_config = default_vlm

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

    # --------------------------------------------------
    # LLM
    # --------------------------------------------------

    def get_llm(self) -> BaseChatModel:
        config = self._llm_config

        if config.provider == LlmProvider.OLLAMA and self.is_ollama_reachable:
            return ChatOllama(
                model=config.model_id,
                base_url=f"http://{self._local_ip}:11434",
                temperature=self._temperature,
                format="json"
            )

        elif config.provider == LlmProvider.GEMINI:
            return init_chat_model(
                config.model_id,
                temperature=self._temperature
            )

        raise ValueError(f"Proveedor no soportado: {config.provider}")

    def get_llm_label(self) -> str:
        """
        Returns a readable identifier of the active model.
        Example: 'ollama:llama3' or 'gemini:gemini-2.5-flash'
        """
        return f"{self._llm_config.provider.value}:{self._llm_config.model_id}"

    # --------------------------------------------------
    # Embeddings
    # --------------------------------------------------

    def get_embeddings(self):
        config = self._embedding_config

        if config.provider == LlmProvider.OLLAMA and self.is_ollama_reachable:
            return init_embeddings(
                f"ollama:{config.model_id}",
                base_url=f"http://{self._local_ip}:11434"
            )

        elif config.provider == LlmProvider.GEMINI:
            return init_embeddings(config.model_id)

        raise ValueError(f"Proveedor no soportado: {config.provider}")

    # --------------------------------------------------
    # VLM (Docling)
    # --------------------------------------------------

    def get_vlm_options(self, prompt: str = "OCR the full page to markdown") -> ApiVlmOptions:
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
    # --------------------------------------------------

    def list_models(self) -> List[ModelConfig]:
        models: List[ModelConfig] = []

        # Ollama (dynamic)
        if self.is_ollama_reachable:
            try:
                response = requests.get(f"http://{self._local_ip}:11434/api/tags")
                data = response.json()

                for m in data.get("models", []):
                    models.append(ModelConfig(
                        provider=LlmProvider.OLLAMA,
                        model_id=m["name"],
                        category="chat"
                    ))
            except Exception:
                pass

        # Gemini (static or API-based)
        models.extend([
            ModelConfig(LlmProvider.GEMINI, "google_genai:gemini-3.1-flash-lite", "chat"),
            ModelConfig(LlmProvider.GEMINI, "google_genai:gemini-2.5-flash", "chat"),
            ModelConfig(LlmProvider.GEMINI, "google_genai:gemini-2.5-pro", "chat"),
            ModelConfig(LlmProvider.GEMINI, "google_genai:gemini-embedding-2", "embedding"),
        ])

        return models

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @property
    def current_llm(self) -> str:
        return self._llm_config.model_id

    @property
    def current_provider(self) -> LlmProvider:
        return self._llm_config.provider

    def is_local_provider(self) -> bool:
        """
        Returns True if the active model is using a local provider (Ollama).
        """
        return (
            self._llm_config.provider == LlmProvider.OLLAMA
            and self.is_ollama_reachable
        )