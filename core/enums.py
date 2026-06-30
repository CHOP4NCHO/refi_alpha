from enum import Enum


class LlmProvider(Enum):
    GEMINI = 'gemini'
    OLLAMA = 'ollama'


class EvaluationMode(Enum):
    LLM_PIPELINE = "llm_pipeline"
    AGENT_AI = "agent"


class RealEvaluation(Enum):
    FULFILLED = 'Fulfilled'
    NOT_FULFILLED = 'Not Fulfilled'
