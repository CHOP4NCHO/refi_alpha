import functools
import time
import traceback
import re
import ast
from pathlib import Path
from langchain.tools import tool
from codebase_reader.codebase_reader import CodeBaseReader

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
        
        print(f"\n[TOOL_START] Invoke: {tool_func.__name__}({combined_args})")
        try:
            result_raw = tool_func(*args, **kwargs)
            result_str = str(result_raw)
            char_count = len(result_str)
            line_count = len(result_str.splitlines())
            
            if char_count > 300:
                preview = f"{result_str[:297].strip()}... [TRUNCATED]"
            else:
                preview = result_str.strip() if result_str.strip() else "[Empty String]"
            
            print(f"[TOOL_SUCCESS] Payload stats: {line_count} lines, {char_count} chars.")
            print(f"[TOOL_PREVIEW]\n{preview}")
            return result_raw
        except Exception as e:
            error_msg = f"[TOOL_ERROR] Failed during {tool_func.__name__}.\n{type(e).__name__}: {str(e)}"
            print(error_msg)
            return error_msg
        finally:
            print(f"[TOOL_TIME] Completed in {time.time() - start_time:.4f} seconds.")
    return exec

def create_evaluator_toolbelt(reader: CodeBaseReader, vector_store=None) -> list:
    """
    Returns a suite of tools optimized for semantic, structural, and proximity analysis.
    Integrates a Vector Store to enable RAG capabilities within the agent's loop.
    """
    workspace_root = reader.codebase.path

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
            file_path: Relative path of the file from the workspace root.
            start_line: The line number to start reading from (1-indexed).
            end_line: The line number to stop reading at.
        """
        target_path = workspace_root / file_path
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
        Analyzes a file using the Abstract Syntax Tree (AST) to extract classes, methods, and functions.
        Provides a high-level architectural view of the file without polluting the context window.
        Args:
            file_path: Relative path from project root.
        """
        target_path = workspace_root / file_path
        if not target_path.is_file():
            return f"Error: File '{file_path}' not found."
            
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            
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
        except Exception as e:
            return f"Could not parse file structure (might not be a valid Python file): {str(e)}"

    @tool
    @refi_tool_wrapper
    def check_test_coverage_proximity(source_file_path: str) -> str:
        """
        Scans the workspace for matching test suites or specification files related to the source file.
        Args:
            source_file_path: Relative path of the source file under evaluation.
        """
        path_obj = Path(source_file_path)
        search_pattern = f"*{path_obj.stem}*{path_obj.suffix}"
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