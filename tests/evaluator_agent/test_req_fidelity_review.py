"""Unit tests for the ReqFidelityReview dataclass."""
from __future__ import annotations

import pytest

from core.evaluator_agent.evaluator import SingleRequirementEval
from core.evaluator_agent.req_fidelity_review import ReqFidelityReview
from core.enums import EvaluationMode, LlmProvider, RealEvaluation


class TestReqFidelityReviewDefaults:
    def test_default_values(self) -> None:
        review = ReqFidelityReview()
        assert review.debug_mode is False
        assert review.review_date == ""
        assert review.input_tokens == 0
        assert review.output_tokens == 0
        assert review.response_time == 0.0

    def test_default_reviewed_reqs_is_empty_list(self) -> None:
        review = ReqFidelityReview()
        assert review.reviewed_reqs == []
        assert isinstance(review.reviewed_reqs, list)

    def test_default_reviewed_reqs_independent_per_instance(self) -> None:
        """Each instance must own its list (no mutable default sharing)."""
        r1 = ReqFidelityReview()
        r2 = ReqFidelityReview()
        r1.reviewed_reqs.append(SingleRequirementEval("a", "b", True))
        assert r2.reviewed_reqs == []

    def test_default_enum_values(self) -> None:
        review = ReqFidelityReview()
        assert review.llm_provider == LlmProvider.GEMINI
        assert review.evaluation_mode == EvaluationMode.LLM_PIPELINE
        assert review.real_evaluation == RealEvaluation.FULFILLED


class TestReqFidelityReviewCustomValues:
    def test_custom_construction(self) -> None:
        reqs = [
            SingleRequirementEval("REQ-1", "Reasoning A", True),
            SingleRequirementEval("REQ-2", "Reasoning B", False),
        ]
        review = ReqFidelityReview(
            debug_mode=True,
            review_date="2026-01-15",
            reviewed_reqs=reqs,
            input_tokens=500,
            output_tokens=250,
            llm_provider=LlmProvider.OLLAMA,
            evaluation_mode=EvaluationMode.AGENT_AI,
            real_evaluation=RealEvaluation.NOT_FULFILLED,
            response_time=3.14,
        )
        assert review.debug_mode is True
        assert review.review_date == "2026-01-15"
        assert review.reviewed_reqs is reqs
        assert review.input_tokens == 500
        assert review.output_tokens == 250
        assert review.llm_provider == LlmProvider.OLLAMA
        assert review.evaluation_mode == EvaluationMode.AGENT_AI
        assert review.real_evaluation == RealEvaluation.NOT_FULFILLED
        assert review.response_time == 3.14

    def test_llm_provider_accepts_string(self) -> None:
        review = ReqFidelityReview(llm_provider="custom_provider")
        assert review.llm_provider == "custom_provider"

    def test_reviewed_reqs_hold_single_requirement_eval_instances(self) -> None:
        review = ReqFidelityReview(
            reviewed_reqs=[SingleRequirementEval("x", "y", True)]
        )
        assert isinstance(review.reviewed_reqs[0], SingleRequirementEval)
