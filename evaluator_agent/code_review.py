

from dataclasses import dataclass
from pydantic import BaseModel

from codebase_reader.codebase import CodeBase
from requirements_extractor.req_document import ReqDocument, Requirement

@dataclass
class FullfiledRequirement:
    requirement: Requirement
    code_snippets: tuple[str]


class CodeReview(BaseModel):
    codebase: CodeBase
    req_doc: ReqDocument
    reviewed_requirements: list[Requirement]
    fullfiled_requirements: list[FullfiledRequirement]
    pending_requirements: list[Requirement]
    score: float
