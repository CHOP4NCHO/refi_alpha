"""Unit tests for the JsonFormatter."""
from __future__ import annotations

import json
from typing import Any

from core.evaluator_agent.req_fidelity_review import ReqFidelityReview
from core.result_manager.json_formatter import JsonFormatter


class TestJsonFormatter:
    def setup_method(self) -> None:
        self.formatter = JsonFormatter()

    def test_format_returns_valid_json(self, sample_review: ReqFidelityReview) -> None:
        output = self.formatter.format(sample_review)
        # Must not raise
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_json_contains_review_date(self, sample_review: ReqFidelityReview) -> None:
        parsed: dict[str, Any] = json.loads(self.formatter.format(sample_review))
        assert parsed["review_date"] == "2026-07-23"

    def test_json_contains_llm_provider_as_string_value(
        self, sample_review: ReqFidelityReview
    ) -> None:
        parsed: dict[str, Any] = json.loads(self.formatter.format(sample_review))
        assert parsed["llm_provider"] == "gemini"

    def test_json_contains_evaluation_mode_value(
        self, sample_review: ReqFidelityReview
    ) -> None:
        parsed: dict[str, Any] = json.loads(self.formatter.format(sample_review))
        assert parsed["evaluation_mode"] == "llm_pipeline"

    def test_json_contains_real_evaluation_value(
        self, sample_review: ReqFidelityReview
    ) -> None:
        parsed: dict[str, Any] = json.loads(self.formatter.format(sample_review))
        assert parsed["real_evaluation"] == "Fulfilled"

    def test_json_contains_token_usage(
        self, sample_review: ReqFidelityReview
    ) -> None:
        parsed: dict[str, Any] = json.loads(self.formatter.format(sample_review))
        usage = parsed["token_usage"]
        assert usage["input"] == 100
        assert usage["output"] == 50
        assert usage["total"] == 150

    def test_json_total_equals_input_plus_output(
        self, sample_review: ReqFidelityReview
    ) -> None:
        sample_review.input_tokens = 7
        sample_review.output_tokens = 11
        parsed: dict[str, Any] = json.loads(self.formatter.format(sample_review))
        assert parsed["token_usage"]["total"] == 18

    def test_json_reviewed_reqs_structure(
        self, sample_review: ReqFidelityReview
    ) -> None:
        parsed: dict[str, Any] = json.loads(self.formatter.format(sample_review))
        reqs = parsed["reviewed_reqs"]
        assert len(reqs) == 2
        for entry in reqs:
            assert set(entry.keys()) == {
                "initial_description",
                "reasoning",
                "is_fulfilled",
            }
        assert reqs[0]["is_fulfilled"] is True
        assert reqs[1]["is_fulfilled"] is False

    def test_json_summary_counts(self, sample_review: ReqFidelityReview) -> None:
        parsed: dict[str, Any] = json.loads(self.formatter.format(sample_review))
        summary = parsed["summary"]
        assert summary["total"] == 2
        assert summary["fulfilled"] == 1
        assert summary["not_fulfilled"] == 1

    def test_json_debug_mode(self, sample_review: ReqFidelityReview) -> None:
        sample_review.debug_mode = True
        parsed: dict[str, Any] = json.loads(self.formatter.format(sample_review))
        assert parsed["debug_mode"] is True

    def test_json_response_time(self, sample_review: ReqFidelityReview) -> None:
        parsed: dict[str, Any] = json.loads(self.formatter.format(sample_review))
        assert parsed["response_time"] == 1.23

    def test_file_extension_is_json(self) -> None:
        assert self.formatter.file_extension == "json"

    def test_json_with_no_reviewed_reqs(self) -> None:
        review = ReqFidelityReview(review_date="2026-01-01")
        parsed: dict[str, Any] = json.loads(self.formatter.format(review))
        assert parsed["reviewed_reqs"] == []
        assert parsed["summary"] == {"total": 0, "fulfilled": 0, "not_fulfilled": 0}
        assert parsed["token_usage"]["total"] == 0

    def test_json_with_string_llm_provider(self) -> None:
        review = ReqFidelityReview(llm_provider="custom_provider")
        parsed: dict[str, Any] = json.loads(self.formatter.format(review))
        assert parsed["llm_provider"] == "custom_provider"
