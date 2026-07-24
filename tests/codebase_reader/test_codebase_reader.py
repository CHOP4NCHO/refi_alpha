"""Unit tests for the codebase_reader package (constants, code_file, codebase, codebase_reader)."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.codebase_reader.code_file import CodeFile, FileContent
from core.codebase_reader.codebase import CodeBase
from core.codebase_reader.codebase_reader import CodeBaseReader
from core.codebase_reader.constants import ACCEPTED_EXTENSIONS, DEFAULT_IGNORES


# =============================================================================
# constants
# =============================================================================
class TestConstants:
    def test_accepted_extensions_contains_common(self) -> None:
        for ext in (".py", ".ts", ".kt", ".js", ".java"):
            assert ext in ACCEPTED_EXTENSIONS

    def test_default_ignores_contains_known_patterns(self) -> None:
        joined = "\n".join(DEFAULT_IGNORES)
        assert "node_modules" in joined
        assert "__pycache__" in joined
        assert "venv" in joined

    def test_default_ignores_includes_dotfiles(self) -> None:
        joined = "\n".join(DEFAULT_IGNORES)
        assert ".*/**" in joined or ".*" in joined


# =============================================================================
# CodeFile
# =============================================================================
class TestCodeFile:
    def test_init_converts_string_to_path(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("x = 1\n", encoding="utf-8")
        cf = CodeFile(str(f))
        assert isinstance(cf.path, Path)
        assert cf.path == f

    def test_get_raw_content(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("hello\nworld\n", encoding="utf-8")
        cf = CodeFile(str(f))
        assert cf.get_raw_content() == "hello\nworld\n"

    def test_get_file_content_line_numbers(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("a\nb\nc\n", encoding="utf-8")
        cf = CodeFile(str(f))
        content = cf.get_file_content()
        assert len(content) == 3
        assert content[0] == FileContent(line_number=1, line_content="a\n")
        assert content[1].line_number == 2
        assert content[2].line_number == 3

    def test_get_code_snippet_valid_range(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("a\nb\nc\nd\ne\n", encoding="utf-8")
        cf = CodeFile(str(f))
        # end_line is exclusive (per docstring): snippet(2, 4) returns lines 2, 3 → "b\nc"
        snippet = cf.get_code_snippet(2, 4)
        assert snippet == "b\nc"

    def test_get_code_snippet_single_line(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("a\nb\nc\nd\ne\n", encoding="utf-8")
        cf = CodeFile(str(f))
        # snippet(2, 3) returns only line 2 → "b" (end is exclusive)
        assert cf.get_code_snippet(2, 3) == "b"

    def test_get_code_snippet_start_below_one(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("a\nb\nc\n", encoding="utf-8")
        cf = CodeFile(str(f))
        # start_line=0 normalizes to 1, end=2 → lines 1..1 → "a"
        assert cf.get_code_snippet(0, 2) == "a"

    def test_get_code_snippet_end_le_start(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("a\nb\nc\n", encoding="utf-8")
        cf = CodeFile(str(f))
        assert cf.get_code_snippet(2, 2) == ""
        assert cf.get_code_snippet(3, 2) == ""

    def test_get_code_snippet_end_beyond_file(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("a\nb\nc\n", encoding="utf-8")
        cf = CodeFile(str(f))
        # end_beyond_file with end=999 returns lines 1..3 (the whole file)
        assert cf.get_code_snippet(1, 999) == "a\nb\nc"

    def test_get_code_snippet_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("", encoding="utf-8")
        cf = CodeFile(str(f))
        assert cf.get_code_snippet(1, 10) == ""


# =============================================================================
# CodeBase
# =============================================================================
class TestCodeBase:
    def test_discovers_accepted_extensions(self, sample_codebase: CodeBase) -> None:
        names = {f.path.name for f in sample_codebase.files}
        assert "app.py" in names
        assert "utils.py" in names
        assert "index.ts" in names

    def test_excludes_non_accepted_extensions(
        self, sample_codebase: CodeBase
    ) -> None:
        names = {f.path.name for f in sample_codebase.files}
        assert "README.md" not in names

    def test_ignores_node_modules(self, sample_codebase: CodeBase) -> None:
        for f in sample_codebase.files:
            assert "node_modules" not in f.path.parts

    def test_ignores_pycache(self, sample_codebase: CodeBase) -> None:
        for f in sample_codebase.files:
            assert "__pycache__" not in f.path.parts
            assert not str(f.path).endswith(".pyc")

    def test_ignores_dotfiles(self, sample_codebase: CodeBase) -> None:
        for f in sample_codebase.files:
            assert ".env" not in f.path.parts

    def test_ignores_build_directory(self, sample_codebase: CodeBase) -> None:
        for f in sample_codebase.files:
            assert "build" not in f.path.parts

    def test_empty_directory(self, tmp_path: Path) -> None:
        cb = CodeBase(str(tmp_path), name="Empty")
        assert cb.files == []

    def test_path_and_name_attributes(self, tmp_path: Path) -> None:
        cb = CodeBase(str(tmp_path), name="MyName")
        assert cb.name == "MyName"
        assert cb.path == tmp_path

    def test_default_name(self, tmp_path: Path) -> None:
        cb = CodeBase(str(tmp_path))
        assert cb.name == "UnnamedCodeBase"

    def test_is_ignored_glob_pattern(self, sample_codebase: CodeBase) -> None:
        assert sample_codebase._is_ignored(Path("foo/test.pyc")) is True
        assert sample_codebase._is_ignored(Path("foo/test.pyo")) is True

    def test_is_ignored_substring_pattern(self, sample_codebase: CodeBase) -> None:
        # 'build' substring pattern should match any path containing 'build'
        assert sample_codebase._is_ignored(Path("build/out.py")) is True
        # 'node_modules' should match nested paths
        assert sample_codebase._is_ignored(Path("node_modules/pkg/x.py")) is True

    def test_is_ignored_returns_false_for_normal(self, sample_codebase: CodeBase) -> None:
        assert sample_codebase._is_ignored(Path("src/app.py")) is False

    def test_custom_ignore_list(self, tmp_path: Path) -> None:
        (tmp_path / "skip_me.py").write_text("x", encoding="utf-8")
        (tmp_path / "keep.py").write_text("x", encoding="utf-8")
        cb = CodeBase(str(tmp_path), name="Custom", ignore=["**/skip_me.py"])
        names = {f.path.name for f in cb.files}
        assert "skip_me.py" not in names
        assert "keep.py" in names

    def test_empty_ignore_list_includes_everything(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x", encoding="utf-8")
        (tmp_path / "b.py").write_text("x", encoding="utf-8")
        cb = CodeBase(str(tmp_path), name="NoIgnore", ignore=[])
        assert len(cb.files) == 2


# =============================================================================
# CodeBaseReader
# =============================================================================
class TestCodeBaseReader:
    def test_init_stores_codebase(
        self, sample_codebase: CodeBase
    ) -> None:
        reader = CodeBaseReader(sample_codebase)
        assert reader.codebase is sample_codebase

    def test_get_directories_dedup(
        self, sample_codebase: CodeBase
    ) -> None:
        reader = CodeBaseReader(sample_codebase)
        dirs = reader.get_directories()
        # All 3 accepted files (app.py, utils.py, index.ts) live in <tmp>/src
        assert len(dirs) == 1
        assert str(Path(dirs[0]).name) == "src"

    def test_get_file_by_index_valid(self, sample_codebase: CodeBase) -> None:
        reader = CodeBaseReader(sample_codebase)
        cf = reader.get_file_by_index(0)
        assert isinstance(cf, CodeFile)

    def test_get_file_by_index_out_of_range(self, sample_codebase: CodeBase) -> None:
        reader = CodeBaseReader(sample_codebase)
        with pytest.raises(IndexError, match="No file at index"):
            reader.get_file_by_index(999)

    def test_get_file_found(self, sample_codebase: CodeBase) -> None:
        reader = CodeBaseReader(sample_codebase)
        target = sample_codebase.files[0]
        assert reader.get_file(target.path) is target

    def test_get_file_not_found(self, sample_codebase: CodeBase) -> None:
        reader = CodeBaseReader(sample_codebase)
        with pytest.raises(IndexError, match="No file at path"):
            reader.get_file(Path("/nonexistent/foo.py"))

    def test_read_file_returns_content(self, sample_codebase: CodeBase) -> None:
        reader = CodeBaseReader(sample_codebase)
        content = reader.read_file(0)
        assert isinstance(content, str)
        assert len(content) > 0

    def test_read_file_invalid_index(self, sample_codebase: CodeBase) -> None:
        reader = CodeBaseReader(sample_codebase)
        with pytest.raises(IndexError):
            reader.read_file(999)

    def test_get_tree_structure(self, sample_codebase: CodeBase) -> None:
        reader = CodeBaseReader(sample_codebase)
        tree = reader.get_tree()
        assert "src" in tree
        assert "_files_" in tree["src"]
        assert isinstance(tree["src"]["_files_"], set)
        assert "app.py" in tree["src"]["_files_"]

    def test_get_tree_empty_codebase(self, tmp_path: Path) -> None:
        empty_cb = CodeBase(str(tmp_path), name="Empty")
        reader = CodeBaseReader(empty_cb)
        assert reader.get_tree() == {}

    def test_show_tree_prints_to_stdout(
        self, sample_codebase: CodeBase, capsys: pytest.CaptureFixture[str]
    ) -> None:
        reader = CodeBaseReader(sample_codebase)
        reader.show_tree()
        captured = capsys.readouterr()
        # show_tree prints the directory name (from path), not the CodeBase name
        assert "src" in captured.out
        assert "app.py" in captured.out
        assert "├──" in captured.out or "└──" in captured.out
