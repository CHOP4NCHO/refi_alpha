import json

from ..evaluator_agent.req_fidelity_review import ReqFidelityReview
from .review_formatter import ReviewFormatter


class JsonFormatter(ReviewFormatter):
    def format(self, review: ReqFidelityReview) -> str:
        fulfilled_count = sum(1 for r in review.reviewed_reqs if r.is_fulfilled)
        total = len(review.reviewed_reqs)

        payload = {
            "review_date": review.review_date,
            "debug_mode": review.debug_mode,
            "llm_provider": (
                review.llm_provider.value
                if hasattr(review.llm_provider, "value")
                else review.llm_provider
            ),
            "evaluation_mode": review.evaluation_mode.value,
            "real_evaluation": review.real_evaluation.value,
            "response_time": review.response_time,
            "token_usage": {
                "input": review.input_tokens,
                "output": review.output_tokens,
                "total": review.input_tokens + review.output_tokens,
            },
            "reviewed_reqs": [
                {
                    "initial_description": req.initial_description,
                    "reasoning": req.reasoning,
                    "is_fulfilled": req.is_fulfilled,
                }
                for req in review.reviewed_reqs
            ],
            "summary": {
                "total": total,
                "fulfilled": fulfilled_count,
                "not_fulfilled": total - fulfilled_count,
            },
        }

        return json.dumps(payload, indent=2, ensure_ascii=False)

    @property
    def file_extension(self) -> str:
        return "json"
