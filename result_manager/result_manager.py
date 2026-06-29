from pathlib import Path

from result_manager.constants import DEFAULT_SAVE_DIR, DEFAULT_SAVE_NAME
from result_manager.req_fidelity_review import ReqFidelityReview


class ResultManager:
    saved_reviews: list[ReqFidelityReview]
    default_save_path: Path
    default_save_name: str

    def __init__(self) -> None:
        self.saved_reviews = []
        self.default_save_path = Path(DEFAULT_SAVE_DIR)
        self.default_save_name = DEFAULT_SAVE_NAME

    def _validate_index(self, index: int) -> None:
        max_index = len(self.saved_reviews)

        if not 0 <= index < max_index:
            raise IndexError(
                f"No review found at index {index}. "
                f"Valid range: 0-{max_index - 1}"
            )

    def add_review(self, review: ReqFidelityReview) -> None:
        self.saved_reviews.append(review)

    def set_default_save_dir(self, dir_path: str) -> None:
        path = Path(dir_path)

        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(
                f"Invalid directory: {dir_path}"
            )

        self.default_save_path = path

    def set_default_save_name(self, save_name: str) -> None:
        self.default_save_name = (
            save_name
            if save_name.lower().endswith(".txt")
            else f"{save_name}.txt"
        )

    def get_code_review(self, index: int) -> ReqFidelityReview:
        self._validate_index(index)
        return self.saved_reviews[index]

    def get_code_review_str(self, index: int) -> str:
        self._validate_index(index)

        review = self.saved_reviews[index]
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
                f"MODEL: {review.llm_provider.value}",
                f"EVALUATION MODE: {review.evaluation_mode.value}",
                f"GROUND TRUTH VALUE: {review.real_evaluation.value}",
                f"RESPONSE TIME: {review.response_time:.2f}s"
            ]
        )

        return "\n".join(lines)

    def save_review(self, index: int, path: Path | None = None) -> None:
        self._validate_index(index)

        output_path = (
            self.default_save_path / self.default_save_name
            if path is None
            else path
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        review      = self.get_code_review(index)
        review_text = self.get_code_review_str(index)

        with output_path.open("a", encoding="utf-8") as file:
            file.write(f"REVIEWED ON {review.review_date}\n")
            file.write(review_text)
            file.write("\n\n")