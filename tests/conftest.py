"""Shared pytest fixtures for the REFI ALPHA test suite."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.evaluator_agent.evaluator import SingleRequirementEval
from core.evaluator_agent.req_fidelity_review import ReqFidelityReview
from core.codebase_reader.codebase import CodeBase
from core.codebase_reader.codebase_reader import CodeBaseReader
from core.enums import EvaluationMode, LlmProvider, RealEvaluation
from core.requirements_extractor.req_document import Requirement


@pytest.fixture
def sample_codebase(tmp_path: Path) -> CodeBase:
    """Create a controlled directory tree with mixed file types and ignored dirs."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "def login(user):\n    return user\n", encoding="utf-8"
    )
    (tmp_path / "src" / "utils.py").write_text(
        "def helper():\n    pass\n", encoding="utf-8"
    )
    (tmp_path / "src" / "index.ts").write_text(
        "export const greet = () => 1;\n", encoding="utf-8"
    )
    (tmp_path / "src" / "README.md").write_text(
        "# Project\nNot source code.\n", encoding="utf-8"
    )

    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.py").write_text(
        "ignored\n", encoding="utf-8"
    )

    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cached.pyc").write_text("", encoding="utf-8")

    (tmp_path / ".env").write_text("SECRET=x", encoding="utf-8")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "out.py").write_text("ignored\n", encoding="utf-8")

    return CodeBase(str(tmp_path), name="TestCodeBase")


@pytest.fixture
def sample_codebase_reader(sample_codebase: CodeBase) -> CodeBaseReader:
    """Wrap the sample codebase in a CodeBaseReader."""
    return CodeBaseReader(sample_codebase)


@pytest.fixture
def sample_requirement() -> Requirement:
    """A single valid Requirement with FUNCTIONAL type."""
    return Requirement(id="REQ-1", description="User login", type="FUNCTIONAL")


@pytest.fixture
def sample_review() -> ReqFidelityReview:
    """A populated ReqFidelityReview with 2 requirements (1 fulfilled, 1 not)."""
    return ReqFidelityReview(
        debug_mode=False,
        review_date="2026-07-23",
        reviewed_reqs=[
            SingleRequirementEval(
                initial_description="REQ-1: User login",
                reasoning="Implemented in src/app.py",
                is_fulfilled=True,
            ),
            SingleRequirementEval(
                initial_description="REQ-2: Caching layer",
                reasoning="No evidence found in codebase",
                is_fulfilled=False,
            ),
        ],
        input_tokens=100,
        output_tokens=50,
        llm_provider=LlmProvider.GEMINI,
        evaluation_mode=EvaluationMode.LLM_PIPELINE,
        real_evaluation=RealEvaluation.FULFILLED,
        response_time=1.23,
    )
