"""Unit tests for the ResultManager class."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.evaluator_agent.req_fidelity_review import ReqFidelityReview
from core.result_manager.json_formatter import JsonFormatter
from core.result_manager.result_manager import ResultManager
from core.result_manager.string_formatter import StringFormatter


class TestResultManagerInMemory:
    def test_init_defaults(self) -> None:
        mgr = ResultManager()
        assert mgr.saved_reviews == []
        assert isinstance(mgr._formatter, StringFormatter)
        assert mgr.default_save_name == "stats/performed_reviews/results.txt"
        assert mgr.default_json_save_name == "stats/performed_reviews/results.json"

    def test_add_and_get_review(self, sample_review: ReqFidelityReview) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        assert mgr.get_code_review(0) is sample_review

    def test_get_review_invalid_index_raises(self) -> None:
        mgr = ResultManager()
        with pytest.raises(IndexError):
            mgr.get_code_review(0)

    def test_get_review_negative_index_raises(
        self, sample_review: ReqFidelityReview
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        with pytest.raises(IndexError):
            mgr.get_code_review(-1)

    def test_validate_index_empty_list(self) -> None:
        mgr = ResultManager()
        with pytest.raises(IndexError, match="Valid range: 0--1"):
            mgr.get_code_review(0)


class TestEnsureExtension:
    def test_adds_txt_when_missing(self) -> None:
        mgr = ResultManager()
        assert mgr._ensure_extension("results", "txt") == "results.txt"

    def test_preserves_existing_txt(self) -> None:
        mgr = ResultManager()
        assert mgr._ensure_extension("results.txt", "txt") == "results.txt"

    def test_preserves_existing_json(self) -> None:
        mgr = ResultManager()
        assert mgr._ensure_extension("results.json", "json") == "results.json"

    def test_adds_json_when_missing(self) -> None:
        mgr = ResultManager()
        assert mgr._ensure_extension("results", "json") == "results.json"

    def test_case_insensitive_existing_extension(self) -> None:
        mgr = ResultManager()
        assert mgr._ensure_extension("results.TXT", "txt") == "results.TXT"


class TestDefaultNames:
    def test_set_default_save_name_appends_txt(self) -> None:
        mgr = ResultManager()
        mgr.set_default_save_name("my_output")
        assert mgr.default_save_name == "my_output.txt"

    def test_set_default_save_name_preserves_existing_txt(self) -> None:
        mgr = ResultManager()
        mgr.set_default_save_name("my_output.txt")
        assert mgr.default_save_name == "my_output.txt"

    def test_set_default_json_save_name_appends_json(self) -> None:
        mgr = ResultManager()
        mgr.set_default_json_save_name("data")
        assert mgr.default_json_save_name == "data.json"

    def test_set_default_json_save_name_preserves_existing_json(self) -> None:
        mgr = ResultManager()
        mgr.set_default_json_save_name("data.json")
        assert mgr.default_json_save_name == "data.json"


class TestFormatter:
    def test_set_formatter_changes_active(self) -> None:
        mgr = ResultManager()
        mgr.set_formatter(JsonFormatter())
        assert isinstance(mgr._formatter, JsonFormatter)

    def test_format_review_as_string(
        self, sample_review: ReqFidelityReview
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        output = mgr.format_review_as_string(0)
        assert "REQ-1" in output
        assert "Fulfilled Requirements: 1/2" in output

    def test_format_review_as_json(
        self, sample_review: ReqFidelityReview
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        output = mgr.format_review_as_json(0)
        parsed = json.loads(output)
        assert parsed["summary"]["total"] == 2

    def test_format_review_uses_active_formatter(
        self, sample_review: ReqFidelityReview
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        mgr.set_formatter(JsonFormatter())
        output = mgr.format_review(0)
        parsed = json.loads(output)
        assert "token_usage" in parsed

    def test_format_review_as_string_ignores_active_formatter(
        self, sample_review: ReqFidelityReview
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        mgr.set_formatter(JsonFormatter())
        output = mgr.format_review_as_string(0)
        assert "TOKEN USAGE STATS" in output

    def test_format_review_as_json_ignores_active_formatter(
        self, sample_review: ReqFidelityReview
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        mgr.set_formatter(StringFormatter())
        output = mgr.format_review_as_json(0)
        assert json.loads(output)["summary"]["total"] == 2

    def test_format_review_invalid_index_raises(
        self, sample_review: ReqFidelityReview
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        with pytest.raises(IndexError):
            mgr.format_review(5)


class TestResolveFormatter:
    def test_txt_returns_string(self) -> None:
        mgr = ResultManager()
        assert isinstance(mgr._resolve_formatter("txt"), StringFormatter)

    def test_string_returns_string(self) -> None:
        mgr = ResultManager()
        assert isinstance(mgr._resolve_formatter("string"), StringFormatter)

    def test_markdown_returns_string(self) -> None:
        mgr = ResultManager()
        assert isinstance(mgr._resolve_formatter("markdown"), StringFormatter)

    def test_md_returns_string(self) -> None:
        mgr = ResultManager()
        assert isinstance(mgr._resolve_formatter("md"), StringFormatter)

    def test_json_returns_json(self) -> None:
        mgr = ResultManager()
        assert isinstance(mgr._resolve_formatter("json"), JsonFormatter)

    def test_uppercase_normalized(self) -> None:
        mgr = ResultManager()
        assert isinstance(mgr._resolve_formatter("JSON"), JsonFormatter)

    def test_whitespace_stripped(self) -> None:
        mgr = ResultManager()
        assert isinstance(mgr._resolve_formatter("  txt  "), StringFormatter)

    def test_invalid_format_raises_value_error(self) -> None:
        mgr = ResultManager()
        with pytest.raises(ValueError, match="Unsupported export format"):
            mgr._resolve_formatter("xml")


class TestSetDefaultSaveDir:
    def test_valid_directory(self, tmp_path: Path) -> None:
        mgr = ResultManager()
        mgr.set_default_save_dir(str(tmp_path))
        assert mgr.default_save_path == tmp_path

    def test_nonexistent_path_raises(self, tmp_path: Path) -> None:
        mgr = ResultManager()
        with pytest.raises(FileNotFoundError):
            mgr.set_default_save_dir(str(tmp_path / "missing"))

    def test_file_path_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("x", encoding="utf-8")
        mgr = ResultManager()
        with pytest.raises(FileNotFoundError):
            mgr.set_default_save_dir(str(f))


class TestSaveReview:
    def test_creates_file_with_content(
        self, sample_review: ReqFidelityReview, tmp_path: Path
    ) -> None:
        mgr = ResultManager()
        mgr.set_default_save_dir(str(tmp_path))
        mgr.add_review(sample_review)
        out = tmp_path / "out.txt"
        mgr.save_review(0, path=out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "REVIEWED ON 2026-07-23" in content
        assert "REQ-1" in content

    def test_appends_on_subsequent_calls(
        self, sample_review: ReqFidelityReview, tmp_path: Path
    ) -> None:
        mgr = ResultManager()
        mgr.set_default_save_dir(str(tmp_path))
        mgr.add_review(sample_review)
        mgr.add_review(sample_review)
        out = tmp_path / "out.txt"
        mgr.save_review(0, path=out)
        mgr.save_review(1, path=out)
        content = out.read_text(encoding="utf-8")
        assert content.count("REVIEWED ON 2026-07-23") == 2

    def test_creates_parent_directories(
        self, sample_review: ReqFidelityReview, tmp_path: Path
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        out = tmp_path / "nested" / "deeper" / "out.txt"
        mgr.save_review(0, path=out)
        assert out.exists()

    def test_save_review_uses_default_path_when_none(
        self, sample_review: ReqFidelityReview, tmp_path: Path
    ) -> None:
        mgr = ResultManager()
        mgr.set_default_save_dir(str(tmp_path))
        mgr.set_default_save_name("auto.txt")
        mgr.add_review(sample_review)
        mgr.save_review(0)
        assert (tmp_path / "auto.txt").exists()

    def test_save_review_invalid_index_raises(
        self, sample_review: ReqFidelityReview, tmp_path: Path
    ) -> None:
        mgr = ResultManager()
        mgr.set_default_save_dir(str(tmp_path))
        with pytest.raises(IndexError):
            mgr.save_review(0, path=tmp_path / "out.txt")


class TestExportReview:
    def test_overwrites_existing_file(
        self, sample_review: ReqFidelityReview, tmp_path: Path
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        out = tmp_path / "out.json"
        out.write_text("STALE", encoding="utf-8")
        mgr.export_review(0, "json", path=out)
        content = out.read_text(encoding="utf-8")
        assert "STALE" not in content
        json.loads(content)  # valid JSON

    def test_json_format_omits_reviewed_on_header(
        self, sample_review: ReqFidelityReview, tmp_path: Path
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        out = tmp_path / "out.json"
        mgr.export_review(0, "json", path=out)
        content = out.read_text(encoding="utf-8")
        assert "REVIEWED ON" not in content

    def test_txt_format_includes_reviewed_on_header(
        self, sample_review: ReqFidelityReview, tmp_path: Path
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        out = tmp_path / "out.txt"
        mgr.export_review(0, "txt", path=out)
        content = out.read_text(encoding="utf-8")
        assert "REVIEWED ON 2026-07-23" in content

    def test_returns_written_path(
        self, sample_review: ReqFidelityReview, tmp_path: Path
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        out = tmp_path / "out.json"
        result = mgr.export_review(0, "json", path=out)
        assert result == out
        assert isinstance(result, Path)

    def test_creates_parent_directories(
        self, sample_review: ReqFidelityReview, tmp_path: Path
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        out = tmp_path / "a" / "b" / "out.json"
        mgr.export_review(0, "json", path=out)
        assert out.exists()

    def test_export_uses_default_path_when_none(
        self, sample_review: ReqFidelityReview, tmp_path: Path
    ) -> None:
        mgr = ResultManager()
        mgr.set_default_save_dir(str(tmp_path))
        mgr.set_default_json_save_name("auto.json")
        mgr.add_review(sample_review)
        result = mgr.export_review(0, "json")
        assert result == tmp_path / "auto.json"

    def test_export_with_invalid_format_raises(
        self, sample_review: ReqFidelityReview, tmp_path: Path
    ) -> None:
        mgr = ResultManager()
        mgr.add_review(sample_review)
        with pytest.raises(ValueError):
            mgr.export_review(0, "xml", path=tmp_path / "out.xml")

    def test_export_invalid_index_raises(
        self, sample_review: ReqFidelityReview, tmp_path: Path
    ) -> None:
        mgr = ResultManager()
        with pytest.raises(IndexError):
            mgr.export_review(5, "json", path=tmp_path / "out.json")
