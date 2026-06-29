from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

from .constants import REQUIREMENT_TYPES



class Requirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    description: str
    type: str

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in REQUIREMENT_TYPES:
            raise ValueError(
                f"Invalid type: {value}. "
                f"Available: {REQUIREMENT_TYPES}"
            )
        return value
    

@dataclass
class ReqDocument:
    path: Path
    name: str
    requirements: list[Requirement]

    def __init__(self, path: str):
        self.path = Path(path)
        self.name = self.path.name
        self.requirements = []

    def add_requirement(self, *reqs: Requirement):
        self.requirements.append(*reqs)

