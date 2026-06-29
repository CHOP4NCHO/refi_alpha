import functools
import logging
import time
import re
import ast
from pathlib import Path
from langchain.tools import tool
from ..codebase_reader.codebase_reader import CodeBaseReader

logger = logging.getLogger(__name__)

def refi_tool_wrapper(tool_func):
    """
    Advanced wrapper that logs precise input arguments, execution safety metrics,
    and a short output preview to help trace agent looping and redundancy.
    """
    @functools.wraps(tool_func)
    def exec(*args, **kwargs):
        start_time = time.time()
        args_list = [repr(a) for a in args]
        kwargs_list = [f"{k}={repr(v)}" for k, v in kwargs.items()]
        combined_args = ", ".join(args_list + kwargs_list)
        
        logger.info(f"[TOOL_START] Invoke: {tool_func.__name__}({combined_args})")
        try:
            result_raw = tool_func(*args, **kwargs)
            result_str = str(result_raw)
            char_count = len(result_str)
            line_count = len(result_str.splitlines())
            
            logger.info(f"[TOOL_SUCCESS] Payload stats: {line_count} lines, {char_count} chars.")
            return result_raw
        except Exception as e:
            error_msg = f"[TOOL_ERROR] Failed during {tool_func.__name__}.\n{type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            return error_msg
        finally:
            logger.info(f"[TOOL_TIME] Completed in {time.time() - start_time:.4f} seconds.")
    return exec

def create_evaluator_toolbelt(reader: CodeBaseReader, vector_store=None, allowed_files: list = None) -> list:
    """
    Returns a suite of tools optimized for semantic, structural, and proximity analysis.
    Integrates a Vector Store to enable RAG capabilities within the agent's loop.
    """
    workspace_root = reader.codebase.path

    def resolve_file_path(file_path: str) -> Path:
        """
        Intelligently resolves absolute, relative, partial, or filename paths to their correct local Path.
        """
        # 1. Try direct absolute path
        p = Path(file_path)
        if p.is_file():
            return p
        
        # 2. Try relative path from workspace root
        p = workspace_root / file_path
        if p.is_file():
            return p
            
        # 3. Try fallback search within the codebase files
        norm_path = file_path.replace("\\", "/").strip("/")
        search_pool = allowed_files if allowed_files else reader.codebase.files
        for code_file in search_pool:
            abs_str = str(code_file.path).replace("\\", "/")
            if abs_str.endswith(norm_path) or code_file.path.name == norm_path:
                return Path(code_file.path)
                
        # Return default fallback
        return workspace_root / file_path

    @tool
    @refi_tool_wrapper
    def query_codebase_rag(semantic_query: str) -> str:
        """
        Performs a semantic similarity search across the entire codebase using a vector store.
        Ideal for locating files, classes, or blocks associated with abstract concepts (e.g., 'rate limiter', 'auth validation').
        Args:
            semantic_query: Natural language description of what you are looking for in the code.
        """
        if vector_store is None:
            return "Error: The RAG vector store is not initialized or injected into this agent."
        
        try:
            # Retrieve top 4 most relevant document/code snippets
            docs = vector_store.similarity_search(semantic_query, k=4)
            if not docs:
                return "No relevant code snippets or files found for the given semantic query."
            
            formatted_chunks = []
            for idx, doc in enumerate(docs, 1):
                filepath = doc.metadata.get("source", "Unknown Path")
                formatted_chunks.append(f"--- Chunk {idx} | File: {filepath} ---\n{doc.page_content}\n")
            return "\n".join(formatted_chunks)
        except Exception as e:
            return f"Error executing RAG query: {str(e)}"

    @tool
    @refi_tool_wrapper
    def read_specific_file_lines(file_path: str, start_line: int = 1, end_line: int = 150) -> str:
        """
        Reads the absolute content of a specific file within a defined line range.
        Use this after query_codebase_rag points you to a target candidate file.
        Args:
            file_path: Relative or absolute path of the file.
            start_line: The line number to start reading from (1-indexed).
            end_line: The line number to stop reading at.
        """
        target_path = resolve_file_path(file_path)
        if not target_path.is_file():
            return f"Error: Target file '{file_path}' does not exist in workspace."
        
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            start = max(1, start_line) - 1
            end = min(total_lines, end_line)
            
            output = [f"--- Inspecting {file_path} (Lines {start+1} to {end} of {total_lines}) ---"]
            for i in range(start, end):
                output.append(f"{i+1}: {lines[i].rstrip()}")
            return "\n".join(output)
        except Exception as e:
            return f"Error reading file stream: {str(e)}"

    @tool
    @refi_tool_wrapper
    def get_file_structure_summary(file_path: str) -> str:
        """
        Analyzes a file (Python, Kotlin, TypeScript, Java, etc.) to extract classes, methods, and functions.
        Provides a high-level architectural view of the file without polluting the context window.
        Args:
            file_path: Relative or absolute path of the file.
        """
        target_path = resolve_file_path(file_path)
        if not target_path.is_file():
            return f"Error: File '{file_path}' not found."
            
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()

            # If it's a Python file, try using the standard library AST parser first
            if target_path.suffix == ".py":
                try:
                    tree = ast.parse(content)
                    summary = [f"Structure of {file_path}:"]
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef):
                            summary.append(f"Class: {node.name}")
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    summary.append(f"  - Method: {item.name}")
                        elif isinstance(node, ast.FunctionDef):
                            summary.append(f"Function: {node.name}")
                    return "\n".join(summary)
                except Exception:
                    pass # Fallback to regex-based parsing if AST fails

            # Language-agnostic structural parser (Kotlin, TS, Java, etc.)
            summary = [f"Structure of {file_path}:"]
            lines = content.splitlines()
            for line in lines:
                line_stripped = line.strip()
                # Skip comments and empty lines
                if not line_stripped or line_stripped.startswith("//") or line_stripped.startswith("/*") or line_stripped.startswith("*"):
                    continue
                
                # Check for class, interface, or object definitions
                class_match = re.search(r"\b(class|interface|object|struct)\s+(\w+)", line_stripped)
                if class_match:
                    summary.append(f"{class_match.group(1).capitalize()}: {class_match.group(2)}")
                    continue
                
                # Check for functions/methods (e.g., fun name, function name, public void name, const name = async...)
                fun_match = re.search(r"\b(fun|function)\s+(\w+)", line_stripped)
                if fun_match:
                    summary.append(f"  - Method/Function: {fun_match.group(2)}")
                    continue
                
                # Java/C# style methods: e.g. public void myMethod( or private String getSomething(
                java_method_match = re.search(r"\b(public|private|protected|internal)\s+(?:static\s+)?([\w<>\d]+)\s+(\w+)\s*\(", line_stripped)
                if java_method_match:
                    method_name = java_method_match.group(3)
                    if method_name not in ("class", "interface", "fun", "function", "if", "for", "while", "switch"):
                        summary.append(f"  - Method: {method_name}")
                        
            return "\n".join(summary)
        except Exception as e:
            return f"Could not parse file structure: {str(e)}"

    @tool
    @refi_tool_wrapper
    def check_test_coverage_proximity(source_file_path: str) -> str:
        """
        Scans the workspace for matching test suites or specification files related to the source file.
        Args:
            source_file_path: Relative or absolute path of the source file under evaluation.
        """
        resolved_path = resolve_file_path(source_file_path)
        path_obj = Path(resolved_path)
        search_pattern = f"*{path_obj.stem}*{path_obj.suffix}"
        if allowed_files:
            allowed_paths = {str(f.path) for f in allowed_files}
            all_matches = list(workspace_root.rglob(search_pattern))
            matches = [m for m in all_matches if str(m) in allowed_paths]
        else:
            matches = list(workspace_root.rglob(search_pattern))
        test_matches = [m for m in matches if 'test' in str(m).lower() or 'spec' in str(m).lower()]
        
        if not test_matches:
            return "No obvious test or specification files found matching this component."
            
        return "Possible test targets found:\n" + "\n".join([str(m.relative_to(workspace_root)) for m in test_matches])

    return [
        query_codebase_rag,
        read_specific_file_lines,
        get_file_structure_summary,
        check_test_coverage_proximity
    ]