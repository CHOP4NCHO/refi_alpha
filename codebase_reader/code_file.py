from dataclasses import dataclass
from pathlib import Path

@dataclass
class FileContent:
    line_number: int
    line_content: str

@dataclass
class CodeFile:
    path: Path

    def __init__(self, path: str):
        self.path = Path(path)
        

    def get_raw_content(self) -> str:
        with open(self.path, 'r') as f:
            return f.read()
        
    def get_file_content(self) -> list[FileContent]:
        with open(self.path, 'r') as f:
            return [FileContent(line_number=i+1, line_content=line) for i, line in enumerate(f)]

    def get_code_snippet(self, start_line: int, end_line: int) -> str:
        """Return a text snippet from start_line to end_line (inclusive of start, exclusive of end).

        Lines are 1-based. This returns only the raw line content joined as a string
        (avoids returning FileContent objects which would render poorly).
        """
        content = self.get_file_content()
        # Normalize bounds and convert to 0-based indices
        if start_line < 1:
            start_line = 1
        if end_line <= start_line:
            return ""

        start_idx = start_line - 1
        end_idx = end_line  # exclusive in slicing

        selected = content[start_idx:end_idx]
        lines = [fc.line_content.rstrip("\n") for fc in selected]
        return "\n".join(lines)

