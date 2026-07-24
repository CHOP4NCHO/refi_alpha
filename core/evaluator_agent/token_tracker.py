from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


class TokenTrackerHandler(BaseCallbackHandler):
    """Callback handler that tracks total used tokens.

    Modern langchain-core uses ``ChatGeneration`` objects that carry a
    ``message`` attribute (an ``AIMessage``) with ``usage_metadata``.
    Legacy ``Generation`` objects have no ``message`` and are silently skipped.
    """

    def __init__(self, evaluator_instance):
        self.evaluator = evaluator_instance

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                if not message:
                    continue

                meta = getattr(message, "usage_metadata", None)
                if not meta:
                    continue

                self.evaluator.total_input_tokens += meta.get("input_tokens", 0)
                self.evaluator.total_output_tokens += meta.get("output_tokens", 0)