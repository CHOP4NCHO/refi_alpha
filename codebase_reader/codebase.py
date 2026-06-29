import os
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from .constants import ACCEPTED_EXTENSIONS, DEFAULT_IGNORES
from .code_file import CodeFile


@dataclass
class CodeBase:
    path: Path
    name: str
    files: list[CodeFile]

    def __init__(
        self,
        path: str = ".",
        name: str = "UnnamedCodeBase",
        ignore: list[str] | None = DEFAULT_IGNORES,
    ):
        self.path = Path(path)
        self.name = name
        self.files = []

        self._ignore = ignore or []

        for root, dirs, files in os.walk(self.path):
            root_path = Path(root)

            dirs[:] = [
                d for d in dirs
                if not self._is_ignored(root_path / d)
            ]

            for filename in files:
                file_path = root_path / filename

                if self._is_ignored(file_path):
                    continue

                if file_path.suffix not in ACCEPTED_EXTENSIONS:
                    continue

                self.files.append(CodeFile(str(file_path)))

    def _is_ignored(self, path: Path) -> bool:
        path_str = str(path)

        for pattern in self._ignore:
            if any(c in pattern for c in "*?[]"):
                if fnmatch(path_str, pattern):
                    return True
            elif pattern in path_str:
                return True

        return False