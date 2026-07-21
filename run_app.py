"""Entry point for PyInstaller packaging."""

import sys
import os

# Add the project root to sys.path so 'ui_pyqt' and 'core' are importable
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from ui_pyqt.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
