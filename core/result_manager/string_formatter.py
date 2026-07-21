from ..evaluator_agent.req_fidelity_review import ReqFidelityReview
from .review_formatter import ReviewFormatter


class StringFormatter(ReviewFormatter):
    def format(self, review: ReqFidelityReview) -> str:
        lines: list[str] = []
        fulfilled_count = 0

        for req in review.reviewed_reqs:
            lines.extend(
                [
                    "==========================",
                    f"Reviewed Requirement: {req.initial_description}",
                    "==========================",
                    f"Status: {'Fulfilled' if req.is_fulfilled else 'Not fulfilled'}",
                    f"Reason: {req.reasoning}",
                    "",
                ]
            )

            if req.is_fulfilled:
                fulfilled_count += 1

        lines.extend(
            [
                "===============================",
                f"Fulfilled Requirements: {fulfilled_count}/{len(review.reviewed_reqs)}",
                "===============================",
                "",
                "===============================",
                "TOKEN USAGE STATS",
                f"Input Tokens : {review.input_tokens}",
                f"Output Tokens: {review.output_tokens}",
                f"Total Tokens : {review.input_tokens + review.output_tokens}",
                "===============================",
            ]
        )

        lines.extend(
            [
                "ESTADÍSTICAS DE EVALUACIÓN SUPERVISADA",
                f"DEBUG MODE: {review.debug_mode}",
                f"MODEL: {review.llm_provider}",
                f"EVALUATION MODE: {review.evaluation_mode.value}",
                f"GROUND TRUTH VALUE: {review.real_evaluation.value}",
                f"RESPONSE TIME: {review.response_time:.2f}s",
            ]
        )

        return "\n".join(lines)

    @property
    def file_extension(self) -> str:
        return "txt"
