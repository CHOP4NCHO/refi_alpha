from dataclasses import dataclass, field

from pydantic import BaseModel

from .evaluator import SingleRequirementEval
from ..enums import LlmProvider, EvaluationMode, RealEvaluation


@dataclass
class ReqFidelityReview():
    debug_mode: bool = False
    review_date: str = ""
    reviewed_reqs: list[SingleRequirementEval] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    llm_provider: str | LlmProvider = LlmProvider.GEMINI
    evaluation_mode: EvaluationMode = EvaluationMode.LLM_PIPELINE
    real_evaluation: RealEvaluation = RealEvaluation.FULFILLED
    response_time: float = 0.0
