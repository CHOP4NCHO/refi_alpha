from pathlib import Path

from .constants import (
    DEFAULT_SAVE_DIR,
    DEFAULT_SAVE_NAME,
    DEFAULT_JSON_SAVE_NAME,
)
from .string_formatter import StringFormatter
from .json_formatter import JsonFormatter
from .review_formatter import ReviewFormatter

from ..evaluator_agent.req_fidelity_review import ReqFidelityReview


class ResultManager:
    saved_reviews: list[ReqFidelityReview]
    default_save_path: Path
    default_save_name: str
    default_json_save_name: str
    _formatter: ReviewFormatter

    def __init__(self) -> None:
        self.saved_reviews = []
        self.default_save_path = Path(DEFAULT_SAVE_DIR)
        self.default_save_name = DEFAULT_SAVE_NAME
        self.default_json_save_name = DEFAULT_JSON_SAVE_NAME
        self._formatter = StringFormatter()

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
        self.default_save_name = self._ensure_extension(save_name, "txt")

    def set_default_json_save_name(self, save_name: str) -> None:
        self.default_json_save_name = self._ensure_extension(save_name, "json")

    def _ensure_extension(self, name: str, ext: str) -> str:
        if name.lower().endswith(f".{ext}"):
            return name
        return f"{name}.{ext}"

    def _default_path_for(self, formatter: ReviewFormatter) -> Path:
        if formatter.file_extension == "json":
            return self.default_save_path / self.default_json_save_name
        return self.default_save_path / self.default_save_name

    def get_code_review(self, index: int) -> ReqFidelityReview:
        self._validate_index(index)
        return self.saved_reviews[index]

    def set_formatter(self, formatter: ReviewFormatter) -> None:
        self._formatter = formatter

    def format_review(self, index: int) -> str:
        self._validate_index(index)
        review = self.saved_reviews[index]
        return self._formatter.format(review)

    def format_review_as_string(self, index: int) -> str:
        self._validate_index(index)
        return StringFormatter().format(self.saved_reviews[index])

    def format_review_as_json(self, index: int) -> str:
        self._validate_index(index)
        return JsonFormatter().format(self.saved_reviews[index])

    def save_review(self, index: int, path: Path | None = None) -> None:
        self._validate_index(index)

        output_path = path if path is not None else self._default_path_for(self._formatter)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        review = self.saved_reviews[index]
        review_text = self._formatter.format(review)

        with output_path.open("a", encoding="utf-8") as file:
            file.write(f"REVIEWED ON {review.review_date}\n")
            file.write(review_text)
            file.write("\n\n")

    def export_review(
        self,
        index: int,
        format: str,
        path: Path | None = None,
    ) -> Path:
        self._validate_index(index)
        formatter = self._resolve_formatter(format)

        output_path = path if path is not None else self._default_path_for(formatter)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        review = self.saved_reviews[index]
        review_text = formatter.format(review)

        with output_path.open("w", encoding="utf-8") as file:
            if formatter.file_extension == "json":
                file.write(review_text)
            else:
                file.write(f"REVIEWED ON {review.review_date}\n")
                file.write(review_text)
                file.write("\n\n")

        return output_path

    def _resolve_formatter(self, format: str) -> ReviewFormatter:
        key = format.strip().lower()
        if key in ("string", "txt", "markdown", "md"):
            return StringFormatter()
        if key in ("json",):
            return JsonFormatter()
        raise ValueError(
            f"Unsupported export format: '{format}'. "
            "Use 'string' (alias: 'txt', 'markdown'/'md') or 'json'."
        )
