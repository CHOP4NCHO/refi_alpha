from dataclasses import dataclass
from pathlib import Path

from .constants import ACCEPTED_EXTENSIONS
from .code_file import CodeFile


@dataclass
class CodeBase:
    path: Path
    name: str
    files: list[CodeFile]

    def __init__(self, path: str = ".", name: str = "UnnamedCodeBase"):
        self.path = Path(path)
        self.name = name
        self.files = []
        for x in self.path.rglob('*'):
            if x.is_file() and x.suffix in ACCEPTED_EXTENSIONS:
                self.files.append(CodeFile(path=str(x)))


    