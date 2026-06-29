


from dataclasses import dataclass, field
from enum import Enum

from evaluator_agent.evaluator import SingleRequirementEval

class LlmProvider(Enum):
    GEMINI = 'gemini3.1-flash'
    OLLAMA = 'ollama'

class EvaluationMode(Enum):
    LLM_PIPELINE = "llm_pipeline"
    AGENT_AI = "agent"

class RealEvaluation(Enum):
    FULFILLED = 'Fulfilled'
    NOT_FULFILLED = 'Not Fulfilled'

@dataclass
class ReqFidelityReview:
    debug_mode: bool = False
    review_date: str = ""
    reviewed_reqs: list[SingleRequirementEval] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    llm_provider: LlmProvider = LlmProvider.GEMINI
    evaluation_mode: EvaluationMode = EvaluationMode.LLM_PIPELINE
    real_evaluation: RealEvaluation = RealEvaluation.FULFILLED
    response_time: float = 0.0

    
