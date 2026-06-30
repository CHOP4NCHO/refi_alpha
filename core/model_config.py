from dataclasses import dataclass
from .enums import LlmProvider

@dataclass
class ModelConfig:
    provider: LlmProvider | None = None
    model_id: str | None = None
    category: str = "chat"  # chat | embedding | vlm

    def is_configured(self) -> bool:
        return self.provider is not None and self.model_id is not None