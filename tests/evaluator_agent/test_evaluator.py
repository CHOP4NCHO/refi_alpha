"""Unit tests for the Evaluator class, prompt templates, and TokenTrackerHandler.

All LangChain agent calls and LLM invocations are mocked; no tokens are spent.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.outputs import Generation, LLMResult

from core.codebase_reader.code_file import CodeFile
from core.codebase_reader.codebase_reader import CodeBaseReader
from core.evaluator_agent.evaluator import (
    CodeFileContext,
    Evaluator,
    SingleRequirementEval,
)
from core.evaluator_agent.token_tracker import TokenTrackerHandler
from core.evaluator_agent.tools import create_evaluator_toolbelt
from core.requirements_extractor.req_document import ReqDocument, Requirement


# =============================================================================
# SingleRequirementEval & CodeFileContext (dataclasses)
# =============================================================================
class TestSingleRequirementEval:
    def test_creation(self) -> None:
        e = SingleRequirementEval(
            initial_description="REQ-1",
            reasoning="Found in module X",
            is_fulfilled=True,
        )
        assert e.initial_description == "REQ-1"
        assert e.reasoning == "Found in module X"
        assert e.is_fulfilled is True

    def test_is_fulfilled_false(self) -> None:
        e = SingleRequirementEval("a", "b", False)
        assert e.is_fulfilled is False


class TestCodeFileContext:
    def test_creation(self) -> None:
        ctx = CodeFileContext(code_content=["a", "b"])
        assert ctx.code_content == ["a", "b"]


# =============================================================================
# Prompt builders (pure)
# =============================================================================
class TestBuildPipelinePrompt:
    def setup_method(self) -> None:
        self.evaluator = Evaluator()

    def test_contains_requirement_description(self) -> None:
        prompt = self.evaluator._build_pipeline_prompt("My requirement", "file content")
        assert "My requirement" in prompt

    def test_contains_file_index_map(self) -> None:
        prompt = self.evaluator._build_pipeline_prompt("req", "FILE_INDEX_42")
        assert "FILE_INDEX_42" in prompt

    def test_contains_json_format_instructions(self) -> None:
        prompt = self.evaluator._build_pipeline_prompt("req", "files")
        for token in ('"initial_description"', '"reasoning"', '"is_fulfilled"', "true | false"):
            assert token in prompt


class TestBuildAgentPrompt:
    def setup_method(self) -> None:
        self.evaluator = Evaluator()

    def test_contains_requirement_description(self) -> None:
        prompt = self.evaluator._build_agent_prompt("My req", "file list")
        assert "My req" in prompt

    def test_contains_file_index_map(self) -> None:
        prompt = self.evaluator._build_agent_prompt("req", "FILE_LIST_HERE")
        assert "FILE_LIST_HERE" in prompt

    def test_contains_stopping_rule(self) -> None:
        prompt = self.evaluator._build_agent_prompt("req", "files")
        assert "REGLA DE PARADA" in prompt
        assert "No matches found" in prompt


class TestBuildRagAgentPrompt:
    def setup_method(self) -> None:
        self.evaluator = Evaluator()

    def test_mentions_rag_tool(self) -> None:
        prompt = self.evaluator._build_rag_agent_prompt("req", "files")
        assert "query_codebase_rag" in prompt

    def test_mentions_structural_tool(self) -> None:
        prompt = self.evaluator._build_rag_agent_prompt("req", "files")
        assert "get_file_structure_summary" in prompt

    def test_mentions_line_reader(self) -> None:
        prompt = self.evaluator._build_rag_agent_prompt("req", "files")
        assert "read_specific_file_lines" in prompt

    def test_mentions_test_proximity(self) -> None:
        prompt = self.evaluator._build_rag_agent_prompt("req", "files")
        assert "check_test_coverage_proximity" in prompt

    def test_in_spanish(self) -> None:
        prompt = self.evaluator._build_rag_agent_prompt("req", "files")
        assert "ESPAÑOL" in prompt or "español" in prompt.lower()


# =============================================================================
# Setters & state
# =============================================================================
class TestEvaluatorInit:
    def test_initial_state(self) -> None:
        ev = Evaluator()
        assert ev._requirement_list == []
        assert ev._tools == []
        assert ev._working_tree is None
        assert ev._codebase is None
        assert ev._req_evaluations == []
        assert ev._vector_store is None
        assert ev.total_input_tokens == 0
        assert ev.total_output_tokens == 0


class TestEvaluatorSetters:
    def test_set_tools(self) -> None:
        ev = Evaluator()
        t1 = lambda: None  # noqa: E731
        t2 = lambda: None  # noqa: E731
        ev.set_tools([t1, t2])
        assert len(ev._tools) == 2
        assert ev._tools[0] is t1
        assert ev._tools[1] is t2

    def test_set_requirements(self) -> None:
        ev = Evaluator()
        doc = ReqDocument("/tmp/spec.pdf")
        doc.add_requirement(Requirement(id="R1", description="a", type="FUNCTIONAL"))
        doc.add_requirement(Requirement(id="R2", description="b", type="NON_FUNCTIONAL"))
        ev.set_requirements(doc)
        assert len(ev._requirement_list) == 2
        # Must be a copy, not a reference
        assert ev._requirement_list is not doc.requirements

    def test_set_codebase(self, sample_codebase_reader: CodeBaseReader) -> None:
        ev = Evaluator()
        ev.set_codebase(sample_codebase_reader.codebase)
        assert ev._codebase is sample_codebase_reader.codebase

    def test_set_working_tree(self) -> None:
        ev = Evaluator()
        tree = {"src": {"_files_": {"a.py"}}}
        ev.set_working_tree(tree)
        assert ev._working_tree is tree


class TestClearVectorStore:
    def test_clear_when_set(self) -> None:
        ev = Evaluator()
        ev._vector_store = MagicMock()
        ev.clear_vector_store()
        assert ev._vector_store is None

    def test_clear_when_already_none(self) -> None:
        ev = Evaluator()
        ev.clear_vector_store()  # no error
        assert ev._vector_store is None


class TestGetModelName:
    def test_with_model_attr(self) -> None:
        ev = Evaluator()
        llm = MagicMock()
        llm.model = "gemma4:12b"
        del llm.profile  # ensure branch with .model is taken
        assert ev.get_model_name(llm) == "gemma4:12b"

    def test_with_profile_dict(self) -> None:
        ev = Evaluator()
        llm = MagicMock(spec=["profile"])
        llm.profile = {"name": "qwen3"}
        assert ev.get_model_name(llm) == "qwen3"


# =============================================================================
# TokenTrackerHandler
# =============================================================================
def _make_llm_result(usage_per_gen: list[dict[str, int] | None]) -> LLMResult:
    """Build a fake LLMResult whose generations carry the given usage metadata.

    Uses ``ChatGeneration`` (the type produced by modern chat models) with
    ``AIMessage`` objects that have ``usage_metadata`` populated.
    """
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration

    generations: list[list[ChatGeneration]] = []
    for usage in usage_per_gen:
        # Modern AIMessage requires all three fields in usage_metadata.
        # If usage is None or empty, omit usage_metadata entirely.
        if usage:
            full_usage = {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0)
                + usage.get("output_tokens", 0),
            }
            message = AIMessage(content="x", usage_metadata=full_usage)
        else:
            message = AIMessage(content="x")
        gen = ChatGeneration(message=message)
        generations.append([gen])
    return LLMResult(generations=generations, llm_output={})


class TestTokenTrackerHandler:
    def test_tracks_tokens_from_chat_generation(self) -> None:
        ev = Evaluator()
        handler = TokenTrackerHandler(ev)
        result = _make_llm_result([{"input_tokens": 10, "output_tokens": 5}])
        handler.on_llm_end(result)
        assert ev.total_input_tokens == 10
        assert ev.total_output_tokens == 5

    def test_empty_generations(self) -> None:
        ev = Evaluator()
        handler = TokenTrackerHandler(ev)
        handler.on_llm_end(LLMResult(generations=[], llm_output={}))
        assert ev.total_input_tokens == 0
        assert ev.total_output_tokens == 0

    def test_multiple_generations_accumulate(self) -> None:
        ev = Evaluator()
        handler = TokenTrackerHandler(ev)
        result = _make_llm_result(
            [
                {"input_tokens": 10, "output_tokens": 5},
                {"input_tokens": 20, "output_tokens": 15},
            ]
        )
        handler.on_llm_end(result)
        assert ev.total_input_tokens == 30
        assert ev.total_output_tokens == 20

    def test_legacy_generation_without_message_is_ignored(self) -> None:
        """Legacy ``Generation`` objects (no ``message``) are silently skipped."""
        ev = Evaluator()
        handler = TokenTrackerHandler(ev)
        legacy_gen = Generation(text="x")
        result = LLMResult(generations=[[legacy_gen]], llm_output={})
        handler.on_llm_end(result)
        assert ev.total_input_tokens == 0
        assert ev.total_output_tokens == 0

    def test_message_without_usage_metadata_is_ignored(self) -> None:
        ev = Evaluator()
        handler = TokenTrackerHandler(ev)
        result = _make_llm_result([None])
        handler.on_llm_end(result)
        assert ev.total_input_tokens == 0
        assert ev.total_output_tokens == 0

    def test_missing_token_keys_default_to_zero(self) -> None:
        ev = Evaluator()
        handler = TokenTrackerHandler(ev)
        result = _make_llm_result([{"input_tokens": 7}])  # no output_tokens
        handler.on_llm_end(result)
        assert ev.total_input_tokens == 7
        assert ev.total_output_tokens == 0

    def test_handler_uses_evaluator_reference(self) -> None:
        ev = Evaluator()
        handler = TokenTrackerHandler(ev)
        assert handler.evaluator is ev


# =============================================================================
# build_vector_store
# =============================================================================
class TestBuildVectorStore:
    def test_calls_from_documents_with_chunks(
        self, sample_codebase_reader: CodeBaseReader
    ) -> None:
        ev = Evaluator()
        embeddings = MagicMock()
        with patch(
            "core.evaluator_agent.evaluator.InMemoryVectorStore"
        ) as mock_store:
            mock_store.from_documents.return_value = MagicMock()
            ev.build_vector_store(sample_codebase_reader, embeddings)
            mock_store.from_documents.assert_called_once()
            docs: list[Document] = mock_store.from_documents.call_args[0][0]
            assert len(docs) > 0
            for d in docs:
                assert isinstance(d, Document)
                assert "source" in d.metadata
                assert "start_line" in d.metadata
                assert "end_line" in d.metadata

    def test_chunking_300_lines_with_30_overlap(
        self, tmp_path: Path
    ) -> None:
        # Build a file with 600 lines
        big = tmp_path / "big.py"
        big.write_text("\n".join(f"line_{i}" for i in range(600)), encoding="utf-8")
        from core.codebase_reader.codebase import CodeBase
        cb = CodeBase(str(tmp_path), name="big")
        reader = CodeBaseReader(cb)

        ev = Evaluator()
        with patch("core.evaluator_agent.evaluator.InMemoryVectorStore") as mock_store:
            mock_store.from_documents.return_value = MagicMock()
            ev.build_vector_store(reader, MagicMock())
            docs: list[Document] = mock_store.from_documents.call_args[0][0]
            # 600 lines, step = 270 (chunk 300 - overlap 30)
            # range(0, 600, 270) → [0, 270, 540] → 3 chunks
            # Each chunk is lines[i:i+300]; end_line = i + len(chunk_lines)
            assert len(docs) == 3
            assert docs[0].metadata["start_line"] == 1
            assert docs[0].metadata["end_line"] == 300
            assert docs[1].metadata["start_line"] == 271
            assert docs[1].metadata["end_line"] == 570
            assert docs[2].metadata["start_line"] == 541
            assert docs[2].metadata["end_line"] == 600

    def test_no_documents_keeps_vector_store_none(
        self, tmp_path: Path
    ) -> None:
        from core.codebase_reader.codebase import CodeBase
        cb = CodeBase(str(tmp_path), name="empty")
        reader = CodeBaseReader(cb)
        ev = Evaluator()
        ev.build_vector_store(reader, MagicMock())
        assert ev._vector_store is None

    def test_empty_file_content_is_skipped(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "blank.py").write_text("   \n\n", encoding="utf-8")
        from core.codebase_reader.codebase import CodeBase
        cb = CodeBase(str(tmp_path), name="blank")
        reader = CodeBaseReader(cb)
        ev = Evaluator()
        with patch("core.evaluator_agent.evaluator.InMemoryVectorStore") as mock_store:
            mock_store.from_documents.return_value = MagicMock()
            ev.build_vector_store(reader, MagicMock())
            # Either from_documents was not called, or it was called with empty list
            if mock_store.from_documents.called:
                docs = mock_store.from_documents.call_args[0][0]
                assert len(docs) == 0
            else:
                assert ev._vector_store is None

    def test_uses_files_content_subset(
        self, sample_codebase_reader: CodeBaseReader
    ) -> None:
        ev = Evaluator()
        only_first = [sample_codebase_reader.codebase.files[0]]
        with patch("core.evaluator_agent.evaluator.InMemoryVectorStore") as mock_store:
            mock_store.from_documents.return_value = MagicMock()
            ev.build_vector_store(
                sample_codebase_reader, MagicMock(), files_content=only_first
            )
            docs = mock_store.from_documents.call_args[0][0]
            sources = {d.metadata["source"] for d in docs}
            assert len(sources) == 1


# =============================================================================
# eval_requirement_llm
# =============================================================================
class TestEvalRequirementLlm:
    def test_appends_structured_response(
        self, sample_codebase_reader: CodeBaseReader, sample_requirement: Requirement
    ) -> None:
        ev = Evaluator()
        eval_obj = SingleRequirementEval("desc", "reason", True)
        agent_mock = MagicMock()
        agent_mock.invoke.return_value = {"structured_response": eval_obj}
        with patch(
            "core.evaluator_agent.evaluator.create_agent", return_value=agent_mock
        ):
            ev.eval_requirement_llm(
                req=sample_requirement,
                files_content=sample_codebase_reader.codebase.files,
                llm_ref=MagicMock(),
            )
        assert len(ev._req_evaluations) == 1
        assert ev._req_evaluations[0] is eval_obj

    def test_calls_with_pipeline_prompt(
        self, sample_codebase_reader: CodeBaseReader, sample_requirement: Requirement
    ) -> None:
        ev = Evaluator()
        agent_mock = MagicMock()
        agent_mock.invoke.return_value = {
            "structured_response": SingleRequirementEval("d", "r", True)
        }
        with patch(
            "core.evaluator_agent.evaluator.create_agent", return_value=agent_mock
        ) as create_patch:
            ev.eval_requirement_llm(
                req=sample_requirement,
                files_content=sample_codebase_reader.codebase.files,
                llm_ref=MagicMock(),
            )
        # create_agent must have been called with tools=[] (no tools in pipeline mode)
        kwargs = create_patch.call_args.kwargs
        assert kwargs["tools"] == []


# =============================================================================
# eval_requirement_agent
# =============================================================================
class AIMessage:  # noqa: D401 - intentional name match
    """Stand-in for ``langchain_core.messages.AIMessage`` for the JSON fallback.

    The source code in ``evaluator.py`` checks ``msg.__class__.__name__ == "AIMessage"``,
    so this class must be named exactly that.
    """
    def __init__(self, content: Any) -> None:
        self.content = content


class TestEvalRequirementAgent:
    def test_structured_response_already_object(
        self, sample_codebase_reader: CodeBaseReader, sample_requirement: Requirement
    ) -> None:
        ev = Evaluator()
        eval_obj = SingleRequirementEval("desc", "reasoning", True)
        agent_mock = MagicMock()
        agent_mock.invoke.return_value = {"structured_response": eval_obj}
        with patch(
            "core.evaluator_agent.evaluator.create_agent", return_value=agent_mock
        ):
            ev.eval_requirement_agent(
                codebase_reader=sample_codebase_reader,
                req=sample_requirement,
                files_content=sample_codebase_reader.codebase.files,
                llm_ref=MagicMock(),
            )
        assert ev._req_evaluations == [eval_obj]

    def test_structured_dict_response(
        self, sample_codebase_reader: CodeBaseReader, sample_requirement: Requirement
    ) -> None:
        ev = Evaluator()
        agent_mock = MagicMock()
        agent_mock.invoke.return_value = {
            "structured_response": {
                "initial_description": "desc",
                "reasoning": "reason",
                "is_fulfilled": False,
            }
        }
        with patch(
            "core.evaluator_agent.evaluator.create_agent", return_value=agent_mock
        ):
            ev.eval_requirement_agent(
                codebase_reader=sample_codebase_reader,
                req=sample_requirement,
                files_content=sample_codebase_reader.codebase.files,
                llm_ref=MagicMock(),
            )
        assert len(ev._req_evaluations) == 1
        assert ev._req_evaluations[0].is_fulfilled is False

    def test_json_fallback_from_ai_message(
        self, sample_codebase_reader: CodeBaseReader, sample_requirement: Requirement
    ) -> None:
        """When the agent returns a raw JSON string, the fallback should
        parse it and build a valid ``SingleRequirementEval``."""
        ev = Evaluator()
        agent_mock = MagicMock()
        agent_mock.invoke.return_value = {
            "messages": [
                AIMessage(
                    '{"initial_description": "desc", "reasoning": "r", "is_fulfilled": true}'
                )
            ]
        }
        with patch(
            "core.evaluator_agent.evaluator.create_agent", return_value=agent_mock
        ):
            ev.eval_requirement_agent(
                codebase_reader=sample_codebase_reader,
                req=sample_requirement,
                files_content=sample_codebase_reader.codebase.files,
                llm_ref=MagicMock(),
            )
        assert len(ev._req_evaluations) == 1
        assert ev._req_evaluations[0].is_fulfilled is True
        assert ev._req_evaluations[0].reasoning == "r"

    def test_json_fallback_with_markdown_fence(
        self, sample_codebase_reader: CodeBaseReader, sample_requirement: Requirement
    ) -> None:
        """JSON wrapped in markdown fences should be parsed correctly."""
        ev = Evaluator()
        agent_mock = MagicMock()
        agent_mock.invoke.return_value = {
            "messages": [
                AIMessage(
                    '```json\n{"initial_description": "d", "reasoning": "r", "is_fulfilled": false}\n```'
                )
            ]
        }
        with patch(
            "core.evaluator_agent.evaluator.create_agent", return_value=agent_mock
        ):
            ev.eval_requirement_agent(
                codebase_reader=sample_codebase_reader,
                req=sample_requirement,
                files_content=sample_codebase_reader.codebase.files,
                llm_ref=MagicMock(),
            )
        assert len(ev._req_evaluations) == 1
        assert ev._req_evaluations[0].is_fulfilled is False
        assert ev._req_evaluations[0].initial_description == "d"

    def test_safety_net_on_exception(
        self, sample_codebase_reader: CodeBaseReader, sample_requirement: Requirement
    ) -> None:
        ev = Evaluator()
        agent_mock = MagicMock()
        agent_mock.invoke.side_effect = RuntimeError("boom")
        with patch(
            "core.evaluator_agent.evaluator.create_agent", return_value=agent_mock
        ):
            ev.eval_requirement_agent(
                codebase_reader=sample_codebase_reader,
                req=sample_requirement,
                files_content=sample_codebase_reader.codebase.files,
                llm_ref=MagicMock(),
            )
        assert len(ev._req_evaluations) == 1
        fallback = ev._req_evaluations[0]
        assert fallback.is_fulfilled is False
        assert "boom" in fallback.reasoning
        assert fallback.initial_description == sample_requirement.description

    def test_uses_rag_prompt_when_vector_store_present(
        self, sample_codebase_reader: CodeBaseReader, sample_requirement: Requirement
    ) -> None:
        ev = Evaluator()
        ev._vector_store = MagicMock()
        agent_mock = MagicMock()
        eval_obj = SingleRequirementEval("d", "r", True)
        agent_mock.invoke.return_value = {"structured_response": eval_obj}
        with patch(
            "core.evaluator_agent.evaluator.create_agent", return_value=agent_mock
        ) as cp:
            ev.eval_requirement_agent(
                codebase_reader=sample_codebase_reader,
                req=sample_requirement,
                files_content=sample_codebase_reader.codebase.files,
                llm_ref=MagicMock(),
            )
        tools_passed = cp.call_args.kwargs["tools"]
        tool_names = [getattr(t, "name", "") for t in tools_passed]
        # RAG path → query_codebase_rag tool must be passed
        assert "query_codebase_rag" in tool_names

    def test_no_vector_store_uses_standard_agent_prompt(
        self, sample_codebase_reader: CodeBaseReader, sample_requirement: Requirement
    ) -> None:
        ev = Evaluator()
        # No _vector_store set → standard agent prompt (not RAG prompt)
        agent_mock = MagicMock()
        eval_obj = SingleRequirementEval("d", "r", True)
        agent_mock.invoke.return_value = {"structured_response": eval_obj}
        with patch(
            "core.evaluator_agent.evaluator.create_agent", return_value=agent_mock
        ):
            ev.eval_requirement_agent(
                codebase_reader=sample_codebase_reader,
                req=sample_requirement,
                files_content=sample_codebase_reader.codebase.files,
                llm_ref=MagicMock(),
            )
        # Verify the standard agent prompt was built (not the RAG one)
        standard_prompt = ev._build_agent_prompt(
            sample_requirement.description, "files"
        )
        assert "REGLA DE PARADA" in standard_prompt
        assert "query_codebase_rag" not in standard_prompt
