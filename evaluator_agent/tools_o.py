import functools

import time
import traceback
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
        
        # Format input arguments for logging transparency
        args_list = [repr(a) for a in args]
        kwargs_list = [f"{k}={repr(v)}" for k, v in kwargs.items()]
        combined_args = ", ".join(args_list + kwargs_list)
        
        print(f"\n[TOOL_START] Invoke: {tool_func.__name__}({combined_args})")
        
        try:
            result_raw = tool_func(*args, **kwargs)
            result_str = str(result_raw)
            
            # Compute operational metadata
            char_count = len(result_str)
            line_count = len(result_str.splitlines())
            
            # Generate a brief snapshot of the payload returned
            if char_count > 150:
                preview = f"{result_str[:147].strip()}... [TRUNCATED]"
            else:
                preview = result_str.strip() if result_str.strip() else "[Empty String]"
            
            print(f"[TOOL_SUCCESS] Payload stats: {line_count} lines, {char_count} chars.")
            print(f"[TOOL_PREVIEW] {preview}")
            return result_raw
            
        except Exception as e:
            error_msg = f"[TOOL_ERROR] Failed during {tool_func.__name__}.\n{type(e).__name__}: {str(e)}"
            print(error_msg)
            print(f"[TOOL_STACKTRACE]\n{traceback.format_exc()}")
            return error_msg
            
        finally:
            execution_time = time.time() - start_time
            print(f"[TOOL_TIME] Completed in {execution_time:.4f} seconds.")
            
    return exec

def create_evaluator_toolbelt(reader: CodeBaseReader) -> list:
    """
    Returns the basic exploration tools: List, Read, and Search.
    """
    workspace_root = reader.codebase.path

    @tool
    @refi_tool_wrapper
    def list_directory(directory_path: str = ".") -> str:
        """
        Lists all files and folders in a specific directory.
        Useful to explore the project structure and find relevant files.
        Args:
            directory_path: The relative path of the directory (default is root '.').
        """
        target_path = workspace_root / directory_path
        if not target_path.exists() or not target_path.is_dir():
            return f"Error: The directory '{directory_path}' does not exist or is invalid."
        
        items = []
        for p in target_path.iterdir():
            # Ignore hidden files/folders like .git or .env
            if not p.name.startswith('.'):
                item_type = "[DIR] " if p.is_dir() else "[FILE]"
                items.append(f"{item_type} {p.name}")
                
        if not items:
            return "The directory is empty."
            
        return "\n".join(sorted(items))

    from pathlib import Path

    @tool
    @refi_tool_wrapper
    def read_file_content(file_path: str) -> str:
        """
        Reads and returns the complete content of a file.
        Use this tool to inspect the source code.

        Args:
            file_path: Relative path from the project root.
        """

        try:
            path_obj = Path(file_path)

            if path_obj.parts and path_obj.parts[0] == workspace_root.name:
                path_obj = Path(*path_obj.parts[1:])

            target_path = workspace_root / path_obj

            if not target_path.is_file():
                return (
                    f"Error: The file '{file_path}' does not exist.\n"
                    f"Resolved path: {target_path}"
                )

            with open(target_path, "r", encoding="utf-8") as f:
                return f.read()

        except UnicodeDecodeError:
            return f"Error: '{file_path}' appears to be a binary file."

        except Exception as e:
            return f"Error reading the file '{file_path}': {str(e)}"

    @tool
    @refi_tool_wrapper
    def search_keyword_in_workspace(keyword: str) -> str:
        """
        Searches for exact text across all project files.
        Returns the file path and the lines where it was found.
        Args:
            keyword: The exact text to search for.
        """
        results = []
        for file_path in workspace_root.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for i, line in enumerate(f, 1):
                            if keyword in line:
                                rel_path = file_path.relative_to(workspace_root)
                                results.append(f"{rel_path}:{i} -> {line.strip()}")
                except UnicodeDecodeError:
                    continue # Silently ignore binary decoding errors
                    
        if not results:
            return f"No matches found for '{keyword}'."
        
        output = "\n".join(results)
        # Simple safety limit to avoid context overflow
        if len(output) > 3000:
            return output[:3000] + "\n...[TRUNCATED: Too many results. Be more specific]"
            
        return output


    
    
    return [list_directory, read_file_content, search_keyword_in_workspace]