from dataclasses import dataclass
from .enums import LlmProvider

@dataclass
class ModelConfig:
    provider: LlmProvider
    model_id: str
    category: str = "chat"  # chat | embedding | vlm