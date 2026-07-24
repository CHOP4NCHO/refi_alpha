"""Unit tests for VlmRetryWrapper and RequirementsExtractor.

All Docling, LLM and HTTP calls are mocked. Zero tokens spent.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from core.requirements_extractor.extractor import (
    RequirementsExtractor,
    RequirementsResponse,
)
from core.requirements_extractor.ocr_errors import (
    DocumentConversionError,
    ExtractorConnectionError,
    RequirementsModelError,
)
from core.requirements_extractor.req_document import Requirement
from core.requirements_extractor.vlm_retry import VlmRetryWrapper


# =============================================================================
# VlmRetryWrapper._is_transient
# =============================================================================
class TestIsTransient:
    def setup_method(self) -> None:
        self.wrapper = VlmRetryWrapper(converter=MagicMock(), max_retries=1, base_delay=0)

    @pytest.mark.parametrize("code", [429, 500, 502, 503, 504])
    def test_transient_http_codes(self, code: int) -> None:
        err = Exception(f'Error: {{"code": {code}}}')
        assert self.wrapper._is_transient(err) is True

    @pytest.mark.parametrize("keyword", ["timeout", "timed out", "connection", "unavailable", "high demand"])
    def test_transient_keywords(self, keyword: str) -> None:
        err = Exception(f"Service {keyword} right now")
        assert self.wrapper._is_transient(err) is True

    def test_non_transient_error(self) -> None:
        err = Exception("invalid input format")
        assert self.wrapper._is_transient(err) is False

    def test_transient_503_in_message(self) -> None:
        err = Exception("got 503 from server")
        assert self.wrapper._is_transient(err) is True

    def test_transient_429_in_message(self) -> None:
        err = Exception("rate limit 429 exceeded")
        assert self.wrapper._is_transient(err) is True


# =============================================================================
# VlmRetryWrapper.convert
# =============================================================================
class TestVlmRetryWrapperConvert:
    def test_success_first_try(self) -> None:
        converter = MagicMock()
        converter.convert.return_value = "ok"
        wrapper = VlmRetryWrapper(converter, max_retries=3, base_delay=0)
        assert wrapper.convert(Path("x.pdf")) == "ok"
        assert converter.convert.call_count == 1

    def test_transient_then_success(self) -> None:
        converter = MagicMock()
        converter.convert.side_effect = [
            Exception('{"code": 503}'),
            Exception("timeout"),
            "ok",
        ]
        wrapper = VlmRetryWrapper(converter, max_retries=3, base_delay=0)
        with patch("core.requirements_extractor.vlm_retry.time.sleep") as sleep_mock:
            assert wrapper.convert(Path("x.pdf")) == "ok"
        assert converter.convert.call_count == 3
        # 2 sleeps for 2 transient failures
        assert sleep_mock.call_count == 2

    def test_non_transient_immediate_raise(self) -> None:
        converter = MagicMock()
        converter.convert.side_effect = ValueError("bad input")
        wrapper = VlmRetryWrapper(converter, max_retries=3, base_delay=0)
        with pytest.raises(ValueError, match="bad input"):
            wrapper.convert(Path("x.pdf"))
        assert converter.convert.call_count == 1

    def test_exhausted_retries_raises_last_error(self) -> None:
        converter = MagicMock()
        converter.convert.side_effect = Exception("503 boom")
        wrapper = VlmRetryWrapper(converter, max_retries=3, base_delay=0)
        with patch("core.requirements_extractor.vlm_retry.time.sleep"):
            with pytest.raises(Exception, match="503 boom"):
                wrapper.convert(Path("x.pdf"))
        assert converter.convert.call_count == 3


# =============================================================================
# Helpers
# =============================================================================
def _make_vlm_options(host: str = "localhost", model: str = "test-model") -> MagicMock:
    """Build a mock VLM options object that satisfies the extractor."""
    opts = MagicMock()
    opts.url.host = host
    opts.params = {"model": model}
    return opts


def _make_extractor(
    *,
    is_local: bool = True,
    host: str = "localhost",
    mock_docling_document: Any = None,
) -> tuple[RequirementsExtractor, MagicMock, MagicMock]:
    """Construct a RequirementsExtractor with the heavy Docling stack fully mocked.

    Returns (extractor, llm_mock, converter_mock) so tests can configure them.
    """
    llm_mock = MagicMock()
    vlm_opts = _make_vlm_options(host=host)

    with patch("core.requirements_extractor.extractor.DocumentConverter") as dc_cls, \
         patch("core.requirements_extractor.extractor.PdfFormatOption"), \
         patch("core.requirements_extractor.extractor.InputFormat"), \
         patch("core.requirements_extractor.extractor.VlmPipelineOptions"), \
         patch("core.requirements_extractor.extractor.VlmPipeline"):
        # The constructor uses these to build a converter, then wraps it.
        converter_instance = MagicMock()
        converter_instance.convert.return_value.document = mock_docling_document
        dc_cls.return_value = converter_instance
        extractor = RequirementsExtractor(llm_mock, vlm_opts, is_local=is_local)
    # Replace the wrapper with one we can control
    extractor.extractor = MagicMock(spec=VlmRetryWrapper)
    extractor.extractor.convert.return_value.document = mock_docling_document
    # Pre-populate _current_document so _get_content / _to_markdown succeed
    extractor._current_document = mock_docling_document
    return extractor, llm_mock, extractor.extractor


# =============================================================================
# RequirementsExtractor._check_ocr_service
# =============================================================================
class TestCheckOcrService:
    def test_success(self) -> None:
        extractor, _, _ = _make_extractor()
        response = MagicMock()
        response.raise_for_status = MagicMock()
        with patch("core.requirements_extractor.extractor.requests.get", return_value=response) as get_mock:
            extractor._check_ocr_service()
        get_mock.assert_called_once()
        assert "11434" in get_mock.call_args[0][0]

    def test_connection_error_raises(self) -> None:
        extractor, _, _ = _make_extractor()
        with patch(
            "core.requirements_extractor.extractor.requests.get",
            side_effect=requests.ConnectionError("nope"),
        ):
            with pytest.raises(ExtractorConnectionError, match="No hay conexión"):
                extractor._check_ocr_service()

    def test_http_error_raises(self) -> None:
        extractor, _, _ = _make_extractor()
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError("500")
        with patch(
            "core.requirements_extractor.extractor.requests.get", return_value=response
        ):
            with pytest.raises(ExtractorConnectionError):
                extractor._check_ocr_service()

    def test_uses_configured_ollama_ip(self) -> None:
        extractor, _, _ = _make_extractor(host="192.168.1.50")
        response = MagicMock()
        response.raise_for_status = MagicMock()
        with patch(
            "core.requirements_extractor.extractor.requests.get", return_value=response
        ) as get_mock:
            extractor._check_ocr_service()
        assert "192.168.1.50" in get_mock.call_args[0][0]


# =============================================================================
# RequirementsExtractor.set_document
# =============================================================================
class TestSetDocument:
    def test_file_not_found(self) -> None:
        extractor, _, _ = _make_extractor()
        with pytest.raises(FileNotFoundError):
            extractor.set_document(Path("/nonexistent/spec.pdf"))

    def test_invalid_extension(self, tmp_path: Path) -> None:
        extractor, _, _ = _make_extractor()
        txt = tmp_path / "spec.txt"
        txt.write_text("x", encoding="utf-8")
        with pytest.raises(ValueError, match="must be a PDF"):
            extractor.set_document(txt)

    def test_success_local(self, tmp_path: Path) -> None:
        pdf = tmp_path / "spec.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        doc_mock = MagicMock()
        extractor, _, _ = _make_extractor(mock_docling_document=doc_mock)
        with patch(
            "core.requirements_extractor.extractor.requests.get"
        ) as get_mock:
            get_mock.return_value.raise_for_status = MagicMock()
            extractor.set_document(pdf)
        assert extractor._current_document is doc_mock

    def test_success_cloud_skips_ocr_check(self, tmp_path: Path) -> None:
        pdf = tmp_path / "spec.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        doc_mock = MagicMock()
        extractor, _, _ = _make_extractor(
            is_local=False, mock_docling_document=doc_mock
        )
        with patch(
            "core.requirements_extractor.extractor.requests.get"
        ) as get_mock:
            extractor.set_document(pdf)
        # requests.get must NOT be called when is_local=False
        get_mock.assert_not_called()
        assert extractor._current_document is doc_mock

    def test_conversion_failure_raises(self, tmp_path: Path) -> None:
        pdf = tmp_path / "spec.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        extractor, _, _ = _make_extractor()
        extractor.extractor.convert.side_effect = RuntimeError("docling crashed")
        with patch(
            "core.requirements_extractor.extractor.requests.get"
        ) as get_mock:
            get_mock.return_value.raise_for_status = MagicMock()
            with pytest.raises(DocumentConversionError, match="No fue posible leer"):
                extractor.set_document(pdf)


# =============================================================================
# RequirementsExtractor._get_content & _to_markdown
# =============================================================================
class TestGetContent:
    def test_raises_when_not_set(self) -> None:
        extractor, _, _ = _make_extractor()
        with pytest.raises(FileNotFoundError, match="Current Document is not defined"):
            extractor._get_content()

    def test_returns_current(self) -> None:
        extractor, _, _ = _make_extractor(mock_docling_document="DOC")
        assert extractor._get_content() == "DOC"


class TestToMarkdown:
    def test_raises_when_not_set(self) -> None:
        extractor, _, _ = _make_extractor()
        with pytest.raises(FileNotFoundError):
            extractor._to_markdown()

    def test_returns_markdown(self) -> None:
        doc_mock = MagicMock()
        doc_mock.export_to_markdown.return_value = "# Title\nBody\n"
        extractor, _, _ = _make_extractor(mock_docling_document=doc_mock)
        assert extractor._to_markdown() == "# Title\nBody\n"
        doc_mock.export_to_markdown.assert_called_once()


# =============================================================================
# RequirementsExtractor.get_requirements
# =============================================================================
class TestGetRequirements:
    def test_success(self) -> None:
        doc_mock = MagicMock()
        doc_mock.name = "spec.pdf"
        doc_mock.export_to_markdown.return_value = "# Reqs\n- A\n- B\n"
        extractor, llm, _ = _make_extractor(mock_docling_document=doc_mock)

        expected = RequirementsResponse(
            items=[
                Requirement(id="R1", description="A", type="FUNCTIONAL"),
                Requirement(id="R2", description="B", type="NON_FUNCTIONAL"),
            ]
        )
        llm.with_structured_output.return_value.invoke.return_value = expected

        result = extractor.get_requirements()

        assert isinstance(result.path, Path)
        assert result.name == "spec.pdf"
        assert len(result.requirements) == 2
        # Verify LLM chain was built correctly
        llm.with_structured_output.assert_called_once_with(RequirementsResponse)
        llm.with_structured_output.return_value.invoke.assert_called_once()

    def test_llm_failure_raises_requirements_model_error(self) -> None:
        doc_mock = MagicMock()
        doc_mock.name = "spec.pdf"
        doc_mock.export_to_markdown.return_value = "content"
        extractor, llm, _ = _make_extractor(mock_docling_document=doc_mock)
        llm.with_structured_output.return_value.invoke.side_effect = RuntimeError(
            "LLM down"
        )
        with pytest.raises(RequirementsModelError, match="no pudo extraer"):
            extractor.get_requirements()

    def test_markdown_export_failure_raises(self) -> None:
        doc_mock = MagicMock()
        doc_mock.name = "spec.pdf"
        doc_mock.export_to_markdown.side_effect = RuntimeError("md fail")
        extractor, _, _ = _make_extractor(mock_docling_document=doc_mock)
        with pytest.raises(DocumentConversionError, match="no fue posible interpretar"):
            extractor.get_requirements()

    def test_get_requirements_calls_with_no_document_raises(self) -> None:
        extractor, _, _ = _make_extractor()
        # _to_markdown raises FileNotFoundError which get_requirements wraps
        # in DocumentConversionError
        with pytest.raises(DocumentConversionError):
            extractor.get_requirements()
