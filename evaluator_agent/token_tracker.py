from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

class TokenTrackerHandler(BaseCallbackHandler):
    """Callback handler that tracks total used tokens."""
    def __init__(self, evaluator_instance):
        self.evaluator = evaluator_instance

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                if not message:
                    continue
          
                meta = getattr(message, "usage_metadata", None)
                if meta:
                    self.evaluator.total_input_tokens += meta.get("input_tokens", 0)
                    self.evaluator.total_output_tokens += meta.get("output_tokens", 0)