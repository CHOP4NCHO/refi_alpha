from pathlib import Path

from .code_file import CodeFile
from .codebase import CodeBase


class CodeBaseReader:
    ignore: list[str] = []

    """Constructor for CodeBaseReader"""
    def __init__(self, codebase: CodeBase):
        self.codebase = codebase
    
    def get_directories(self) -> list[str]:
        dirs = set()
        for file in self.codebase.files:
            if file.path not in self.ignore:
                dirs.add(str(file.path.parent))
        return list(dirs)

    def get_file_by_index(self, index: int) -> CodeFile:
        try:
            return self.codebase.files[index]
        except IndexError:
            raise IndexError(f"No file at index {index} in codebase '{self.codebase.name}'.")
        
    def get_file(self, path: Path) -> CodeFile:
        try:
            return next(file for file in self.codebase.files if file.path == path)
        except StopIteration:
            raise IndexError(f"No file at path {path} in codebase '{self.codebase.name}'.")    
        
    def read_file(self, index: int) -> str:
        try:
            code_file = self.codebase.files[index]
            return code_file.get_raw_content()
        except IndexError:
            raise IndexError(f"No file at index {index} in codebase '{self.codebase.name}'.")

    def get_tree(self) -> dict:
        tree = {}
        base_path = Path(self.codebase.path)

        for file in self.codebase.files:
            relative_path = Path(file.path).relative_to(base_path)
            parts = relative_path.parts
            
            current = tree
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current.setdefault("_files_", set()).add(file.path.name)
        return tree


    def show_tree(self) -> None:
        parent_name = Path(self.codebase.path).name
        print(f"└── {parent_name}/")
        tree = self.get_tree()
        self._print_tree(tree, "    ", is_root=True)


    def _print_tree(self, tree: dict, prefix: str, is_root: bool = False) -> None:
        dirs = sorted([k for k in tree.keys() if k != "_files_"])
        files = sorted(tree.get("_files_", []))

        entries = [(d, "dir") for d in dirs] + [(f, "file") for f in files]

        for i, (name, typ) in enumerate(entries):
            is_last = i == len(entries) - 1

            if is_root:
                connector = "└── " if is_last else "├── "
            else:
                connector = "└── " if is_last else "├── "

            if typ == "dir":
                print(f"{prefix}{connector}{name}/")
                extension = "    " if is_last else "│   "
                self._print_tree(tree[name], prefix + extension, is_root=False)
            else:
                print(f"{prefix}{connector}{name}")