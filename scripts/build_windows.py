#!/usr/bin/env python3
"""Build a Windows NSIS installer from Linux.

Requirements:
- NSIS installed on Linux (sudo apt-get install nsis)
- vendor/python-3.12.x-embed-amd64.zip downloaded from python.org
- vendor/get-pip.py downloaded from bootstrap.pypa.io

Output:
- dist/refi-alpha-windows-setup.exe
"""

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
VENDOR_DIR = PROJECT_ROOT / "vendor"
DIST_DIR = PROJECT_ROOT / "dist"
STAGING_DIR = DIST_DIR / "windows" / "staging"
NSIS_SCRIPT = PROJECT_ROOT / "scripts" / "refi-alpha.nsi"
LAUNCHER_TEMPLATE = PROJECT_ROOT / "scripts" / "launcher.bat.template"
OUTPUT_EXE = DIST_DIR / "refi-alpha-windows-setup.exe"
OUTPUT_ZIP = DIST_DIR / "refi-alpha-windows-portable.zip"


def find_embedded_python() -> Path:
    """Find the cached Windows embeddable Python zip."""
    candidates = list(VENDOR_DIR.glob("python-*-embed-amd64.zip"))
    if not candidates:
        print(
            "ERROR: No se encontro Python embebido de Windows en vendor/.\n"
            "Descargalo desde https://www.python.org/downloads/windows/\n"
            "Ejemplo: python-3.12.6-embed-amd64.zip"
        )
        sys.exit(1)
    return candidates[0]


def find_get_pip() -> Path:
    """Find the cached get-pip.py bootstrap script."""
    candidate = VENDOR_DIR / "get-pip.py"
    if not candidate.exists():
        print(
            "ERROR: No se encontro get-pip.py en vendor/.\n"
            "Descargalo desde https://bootstrap.pypa.io/get-pip.py"
        )
        sys.exit(1)
    return candidate


def clean_staging() -> None:
    """Remove previous staging directory."""
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True)


def extract_embedded_python(zip_path: Path) -> Path:
    """Extract embeddable Python into staging/python/."""
    python_dir = STAGING_DIR / "python"
    python_dir.mkdir()
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(python_dir)
    print(f"OK: Python embebido extraido en {python_dir}")
    return python_dir


def fix_python_pth(python_dir: Path) -> None:
    """Uncomment 'import site' in python._pth so pip works."""
    pth_files = list(python_dir.glob("python*._pth"))
    if not pth_files:
        print(f"ERROR: No se encontro archivo ._pth en {python_dir}")
        sys.exit(1)
    pth_file = pth_files[0]
    original = pth_file.read_text(encoding="utf-8")
    fixed = original.replace("#import site", "import site")
    if fixed == original:
        print(f"ADVERTENCIA: No se encontro '#import site' en {pth_file}. Revisar manualmente.")
    pth_file.write_text(fixed, encoding="utf-8")
    print(f"OK: {pth_file} modificado para permitir import site")


def copy_app_code() -> None:
    """Copy application source files into staging/app/."""
    app_dir = STAGING_DIR / "app"
    app_dir.mkdir()

    items = ["core", "ui_pyqt", "requirements.txt", ".env.example", "run_app.py"]
    for item in items:
        src = PROJECT_ROOT / item
        if not src.exists():
            print(f"ERROR: No se encontro {src}")
            sys.exit(1)
        dst = app_dir / item
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    print(f"OK: Codigo de la aplicacion copiado en {app_dir}")


def copy_get_pip(get_pip_path: Path, python_dir: Path) -> None:
    """Copy get-pip.py next to python.exe."""
    shutil.copy2(get_pip_path, python_dir / "get-pip.py")
    print(f"OK: get-pip.py copiado en {python_dir}")


def generate_launcher() -> None:
    """Copy the launcher template into staging root with CRLF line endings."""
    if not LAUNCHER_TEMPLATE.exists():
        print(f"ERROR: No se encontro {LAUNCHER_TEMPLATE}")
        sys.exit(1)
    
    content = LAUNCHER_TEMPLATE.read_text(encoding="utf-8")
    crlf_content = content.replace("\r\n", "\n").replace("\n", "\r\n")
    dst = STAGING_DIR / "refi-alpha.bat"
    dst.write_bytes(crlf_content.encode("utf-8"))
    print(f"OK: Launcher generado en {dst}")


def find_nsis_dir() -> Path:
    """Return the NSIS directory to use.

    Fedora's mingw-nsis package ships only amd64-unicode stubs, while the
    default makensis looks for the x86-unicode stub. When that happens, create
    a temporary NSIS directory with a symlink so the build can proceed without
    touching the system installation.
    """
    system_nsis_dir = Path(os.environ.get("NSISDIR", "/usr/share/nsis"))
    default_stub = "zlib-x86-unicode"
    fallback_stub = "zlib-amd64-unicode"

    stub_path = system_nsis_dir / "Stubs" / default_stub
    if stub_path.exists():
        return system_nsis_dir

    fallback_path = system_nsis_dir / "Stubs" / fallback_stub
    if not fallback_path.exists():
        print(
            f"ERROR: No se encontro el stub de NSIS por defecto ({stub_path}) "
            f"ni la alternativa ({fallback_path})."
        )
        sys.exit(1)

    temp_dir = Path(tempfile.mkdtemp(prefix="nsis-"))
    print(
        f"ADVERTENCIA: makensis espera el stub {default_stub} pero solo existe "
        f"{fallback_stub}. Usando directorio temporal de NSIS: {temp_dir}"
    )
    shutil.copytree(system_nsis_dir, temp_dir, dirs_exist_ok=True)
    os.symlink(
        fallback_path.resolve(),
        temp_dir / "Stubs" / default_stub,
    )

    # Fedora ships plugins only under amd64-unicode. Because makensis thinks
    # we are targeting x86-unicode (default stub name), provide the matching
    # plugin directory by copying the amd64-unicode plugins.
    plugins_dir = temp_dir / "Plugins"
    x86_plugins_dir = plugins_dir / "x86-unicode"
    amd64_plugins_dir = plugins_dir / "amd64-unicode"
    if amd64_plugins_dir.exists() and not x86_plugins_dir.exists():
        shutil.copytree(amd64_plugins_dir, x86_plugins_dir)

    return temp_dir


def create_zip() -> Path:
    """Package the staging directory into a portable zip file."""
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()
    
    archive_name = OUTPUT_ZIP.with_suffix("")
    shutil.make_archive(
        base_name=str(archive_name),
        format="zip",
        root_dir=STAGING_DIR,
    )
    print(f"OK: Paquete portable comprimido en {OUTPUT_ZIP}")
    return OUTPUT_ZIP


def compile_nsis() -> bool:
    """Run makensis to build the installer if available."""
    if not NSIS_SCRIPT.exists():
        print(f"ADVERTENCIA: No se encontro {NSIS_SCRIPT}. Omitiendo instalador NSIS.")
        return False

    try:
        nsis_dir = find_nsis_dir()
    except SystemExit:
        print("ADVERTENCIA: NSIS no configurado adecuadamente. Omitiendo instalador NSIS.")
        return False

    env = os.environ.copy()
    env["NSISDIR"] = str(nsis_dir)

    try:
        subprocess.run(
            ["makensis", str(NSIS_SCRIPT)],
            cwd=PROJECT_ROOT,
            check=True,
            env=env,
        )
    except FileNotFoundError:
        print(
            "INFO: makensis no encontrado. Se omite la creacion del instalador .exe (solo portable .zip)."
        )
        return False
    except subprocess.CalledProcessError as exc:
        print(f"ADVERTENCIA: makensis fallo con codigo {exc.returncode}")
        return False
    finally:
        system_nsis_dir = Path(os.environ.get("NSISDIR", "/usr/share/nsis"))
        if 'nsis_dir' in locals() and nsis_dir != system_nsis_dir:
            shutil.rmtree(nsis_dir, ignore_errors=True)

    if OUTPUT_EXE.exists():
        print(f"OK: Instalador generado en {OUTPUT_EXE}")
        return True
    return False


def main() -> int:
    print("=== REFI ALPHA - Build Windows Package (.zip / .exe) ===")

    if not VENDOR_DIR.exists():
        VENDOR_DIR.mkdir(parents=True)
        print(f"ADVERTENCIA: Creando directorio {VENDOR_DIR}. Copiar Python embebido y get-pip.py.")

    embedded_zip = find_embedded_python()
    get_pip_path = find_get_pip()

    clean_staging()
    python_dir = extract_embedded_python(embedded_zip)
    fix_python_pth(python_dir)
    copy_get_pip(get_pip_path, python_dir)
    copy_app_code()
    generate_launcher()

    # Generar ZIP portable
    create_zip()

    # Intentar generar instalador NSIS si esta disponible
    compile_nsis()

    print("\n=== Build completado ===")
    print(f"Portable Zip: {OUTPUT_ZIP}")
    if OUTPUT_EXE.exists():
        print(f"Instalador EXE: {OUTPUT_EXE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
