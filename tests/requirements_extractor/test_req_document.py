"""Unit tests for the Requirement and ReqDocument models."""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.requirements_extractor.req_document import ReqDocument, Requirement


# =============================================================================
# Requirement
# =============================================================================
class TestRequirement:
    def test_valid_functional(self) -> None:
        r = Requirement(id="R1", description="Login", type="FUNCTIONAL")
        assert r.id == "R1"
        assert r.description == "Login"
        assert r.type == "FUNCTIONAL"

    def test_valid_non_functional(self) -> None:
        r = Requirement(id="R1", description="Fast", type="NON_FUNCTIONAL")
        assert r.type == "NON_FUNCTIONAL"

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            Requirement(id="R1", description="x", type="INVALID")

    def test_frozen_blocks_mutation(self) -> None:
        r = Requirement(id="R1", description="x", type="FUNCTIONAL")
        with pytest.raises(ValidationError):
            r.description = "mutated"  # type: ignore[misc]

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            Requirement(id="R1")  # type: ignore[call-arg]


# =============================================================================
# ReqDocument
# =============================================================================
class TestReqDocument:
    def test_init_sets_path_and_name(self, tmp_path: Path) -> None:
        pdf = tmp_path / "spec.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        doc = ReqDocument(str(pdf))
        assert doc.path == pdf
        assert doc.name == "spec.pdf"

    def test_init_empty_requirements(self, tmp_path: Path) -> None:
        doc = ReqDocument(str(tmp_path / "x.pdf"))
        assert doc.requirements == []

    def test_add_single_requirement(self, tmp_path: Path) -> None:
        doc = ReqDocument(str(tmp_path / "x.pdf"))
        r = Requirement(id="R1", description="x", type="FUNCTIONAL")
        doc.add_requirement(r)
        assert len(doc.requirements) == 1
        assert doc.requirements[0] is r

    def test_delete_existing_requirement(self, tmp_path: Path) -> None:
        doc = ReqDocument(str(tmp_path / "x.pdf"))
        r = Requirement(id="R1", description="x", type="FUNCTIONAL")
        doc.add_requirement(r)
        doc.delete_requirement(r)
        assert doc.requirements == []

    def test_delete_nonexistent_requirement_raises(self, tmp_path: Path) -> None:
        doc = ReqDocument(str(tmp_path / "x.pdf"))
        r = Requirement(id="R1", description="x", type="FUNCTIONAL")
        with pytest.raises(ValueError):
            doc.delete_requirement(r)

    def test_add_multiple_requirements_with_starargs(self, tmp_path: Path) -> None:
        """``add_requirement(*reqs)`` should accept any number of requirements."""
        doc = ReqDocument(str(tmp_path / "x.pdf"))
        r1 = Requirement(id="R1", description="x", type="FUNCTIONAL")
        r2 = Requirement(id="R2", description="y", type="NON_FUNCTIONAL")
        r3 = Requirement(id="R3", description="z", type="FUNCTIONAL")
        doc.add_requirement(r1, r2, r3)
        assert len(doc.requirements) == 3
        assert doc.requirements == [r1, r2, r3]
