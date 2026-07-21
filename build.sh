#!/bin/bash
set -e

echo "=== REFI ALPHA - Build ==="

if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 no encontrado"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

if [[ $(echo "$PYTHON_VERSION < 3.10" | bc) -eq 1 ]]; then
    echo "ERROR: Se requiere Python 3.10+. Version actual: $PYTHON_VERSION"
    exit 1
fi

echo "Creando entorno virtual..."

if [ ! -d venv ]; then
    python3 -m venv venv
fi

source venv/bin/activate

echo "Instalando dependencias..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Archivo .env creado. Edita .env con tus API keys."
fi

echo "Limpiando build anterior..."
rm -rf build dist refi-alpha.spec

echo "Empaquetando con PyInstaller..."

pyinstaller \
    --clean \
    --noconfirm \
    --onedir \
    --name refi-alpha \
    --additional-hooks-dir=hooks \
    --add-data "ui_pyqt:ui_pyqt" \
    --add-data "core:core" \
    --hidden-import langchain \
    --hidden-import langchain_core \
    --hidden-import langchain_ollama \
    --hidden-import docling \
    --hidden-import docling_parse \
    --collect-data docling_parse \
    --hidden-import docling.models.plugins.defaults \
    --copy-metadata docling-slim \
    --hidden-import pydantic \
    --hidden-import ui_pyqt \
    --hidden-import ui_pyqt.landing_page \
    --hidden-import ui_pyqt.main_window \
    --hidden-import ui_pyqt.theme_manager \
    --hidden-import ui_pyqt.config_page \
    --hidden-import ui_pyqt.evaluation_page \
    --hidden-import ui_pyqt.requirements_page \
    --hidden-import ui_pyqt.review_viewer_page \
    --hidden-import ui_pyqt.workspace_page \
    --hidden-import ui_pyqt.components \
    --hidden-import ui_pyqt.workers \
    --hidden-import ui_pyqt.ui_loader \
    --hidden-import ui_pyqt.theme \
    --hidden-import core \
    --hidden-import core.refi_service \
    --hidden-import core.model_provider \
    --hidden-import core.model_factory \
    --hidden-import core.enums \
    --hidden-import core.codebase_reader \
    --hidden-import core.evaluator_agent \
    --hidden-import core.requirements_extractor \
    --hidden-import core.result_manager \
    --exclude-module ttkbootstrap \
    --exclude-module tkinter \
    run_app.py

echo ""
echo "Verificando recursos de docling_parse..."

PDF_RESOURCES="dist/refi-alpha/_internal/docling_parse/pdf_resources"

if [ -d "$PDF_RESOURCES" ]; then
    echo "OK: recursos PDF encontrados en:"
    echo "  $PDF_RESOURCES"
else
    echo "ERROR: no se incluyeron los recursos de docling_parse"
    exit 1
fi

echo ""
echo "=== Build completado ==="
echo "Ejecutable: dist/refi-alpha/refi-alpha"
echo ""
echo "Para ejecutar:"
echo "  cd dist/refi-alpha"
echo "  ./refi-alpha"
