#!/usr/bin/env python3
"""Build a portable Windows zip (no installer).

This creates dist/refi-alpha-windows-portable.zip with:
- python/          Windows embedded Python
- app/             REFI source code
- refi-alpha.bat   Launcher
- README.txt       Instructions

Requirements:
- Same as build_windows.py: vendor/python-3.12.x-embed-amd64.zip and
  vendor/get-pip.py must exist.
"""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
STAGING_DIR = PROJECT_ROOT / "dist" / "windows" / "staging"
OUTPUT_ZIP = PROJECT_ROOT / "dist" / "refi-alpha-windows-portable.zip"

README_CONTENT = """REFI ALPHA - Portable Windows
==============================

1. Extraer este ZIP completamente.
2. Abrir la carpeta extraida.
3. Ejecutar refi-alpha.bat.

Primer arranque:
- Se abrira una ventana de consola.
- Se instalara pip y las dependencias necesarias en el runtime de Python incluido.
- Esperar sin cerrar la ventana.

Cuando diga "Instalacion completada", cerrar la ventana y ejecutar refi-alpha.bat de nuevo.

Para modelos cloud, configurar las claves en:
app\\.env
"""


def ensure_staging() -> None:
    """Make sure the staging directory exists by running build_windows.py."""
    if STAGING_DIR.exists() and (STAGING_DIR / "python" / "python.exe").exists():
        return

    build_script = PROJECT_ROOT / "scripts" / "build_windows.py"
    print("Generando staging con build_windows.py...")
    result = subprocess.run(
        [sys.executable, str(build_script)],
        cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        print("ERROR: No se pudo generar el staging.")
        sys.exit(1)


def build_portable_zip() -> None:
    """Create the portable zip from staging."""
    if not STAGING_DIR.exists():
        print(f"ERROR: No se encontro {STAGING_DIR}")
        sys.exit(1)

    OUTPUT_ZIP.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()

    readme_path = STAGING_DIR / "README.txt"
    readme_path.write_text(README_CONTENT, encoding="utf-8")

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in STAGING_DIR.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(STAGING_DIR))

    print(f"OK: ZIP portable generado en {OUTPUT_ZIP}")


def main() -> int:
    print("=== REFI ALPHA - Build Windows Portable ZIP ===")
    ensure_staging()
    build_portable_zip()
    print(f"\n=== Completado ===")
    print(f"Archivo: {OUTPUT_ZIP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
