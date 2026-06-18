


from dataclasses import dataclass
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
    debug_mode: bool
    review_date: str
    reviewed_reqs: list[SingleRequirementEval]
    input_tokens: int
    output_tokens: int
    llm_provider: LlmProvider
    evaluation_mode: EvaluationMode
    real_evaluation: RealEvaluation

    
