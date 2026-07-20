from enum import Enum


class LlmProvider(Enum):
    GEMINI = 'gemini'
    OLLAMA = 'ollama'
    OPENAI = 'openai'
    CLAUDE = 'claude'


class EvaluationMode(Enum):
    LLM_PIPELINE = "llm_pipeline"
    AGENT_AI = "agent"


class RealEvaluation(Enum):
    FULFILLED = 'Fulfilled'
    NOT_FULFILLED = 'Not Fulfilled'


class RefiOperations(Enum):
    EVALUATE_PIPELINE = "evaluar_pipeline"
    EVALUATE_AGENT = "evaluar_agente"
    IMPORT_PDF = "importar_pdf"
