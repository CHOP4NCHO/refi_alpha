@echo off
setlocal enabledelayedexpansion

echo === REFI ALPHA - Build ===

REM Verificar Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no encontrado
    exit /b 1
)

for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set PYVER=%%i
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    if %%a LSS 3 (
        echo ERROR: Se requiere Python 3.10+. Version actual: %PYVER%
        exit /b 1
    )
    if %%a EQU 3 if %%b LSS 10 (
        echo ERROR: Se requiere Python 3.10+. Version actual: %PYVER%
        exit /b 1
    )
)

REM Crear entorno virtual
if not exist venv (
    echo Creando entorno virtual...
    python -m venv venv
) else (
    echo Entorno virtual existente encontrado.
)

call venv\Scripts\activate.bat

echo Instalando torch CPU-only
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu

REM Instalar dependencias
echo Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM Configurar .env si no existe
if not exist .env (
    copy .env.example .env
    echo Archivo .env creado. Edita .env con tus API keys.
)

REM Limpiar build anterior
echo Limpiando build anterior...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
if exist refi-alpha.spec del refi-alpha.spec

REM Ejecutar PyInstaller
echo Empaquetando con PyInstaller...
pyinstaller ^
    --clean ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --name refi-alpha ^
    --additional-hooks-dir=hooks ^
    --add-data "ui_pyqt;ui_pyqt" ^
    --add-data "core;core" ^
    --hidden-import langchain ^
    --hidden-import langchain_core ^
    --hidden-import langchain_ollama ^
    --hidden-import docling ^
    --hidden-import docling_parse ^
    --hidden-import docling_parse ^
    --collect-data docling_parse ^
    --hidden-import docling.models.plugins.defaults ^
    --copy-metadata docling-slim ^
    --hidden-import pydantic ^
    --hidden-import ui_pyqt ^
    --hidden-import ui_pyqt.landing_page ^
    --hidden-import ui_pyqt.main_window ^
    --hidden-import ui_pyqt.theme_manager ^
    --hidden-import ui_pyqt.config_page ^
    --hidden-import ui_pyqt.evaluation_page ^
    --hidden-import ui_pyqt.requirements_page ^
    --hidden-import ui_pyqt.review_viewer_page ^
    --hidden-import ui_pyqt.workspace_page ^
    --hidden-import ui_pyqt.components ^
    --hidden-import ui_pyqt.workers ^
    --hidden-import ui_pyqt.ui_loader ^
    --hidden-import ui_pyqt.theme ^
    --hidden-import core ^
    --hidden-import core.refi_service ^
    --hidden-import core.model_provider ^
    --hidden-import core.model_factory ^
    --hidden-import core.enums ^
    --hidden-import core.codebase_reader ^
    --hidden-import core.evaluator_agent ^
    --hidden-import core.requirements_extractor ^
    --hidden-import core.result_manager ^
    --exclude-module ttkbootstrap ^
    --exclude-module tkinter ^
    run_app.py

echo.
echo Verificando recursos de docling_parse...

set "PDF_RESOURCES=dist\refi-alpha\_internal\docling_parse\pdf_resources"

if exist "%PDF_RESOURCES%" (
    echo OK: recursos PDF encontrados en:
    echo   %PDF_RESOURCES%
) else (
    echo ERROR: no se incluyeron los recursos de docling_parse
    exit /b 1
)

echo.
echo === Build completado ===
echo Ejecutable: dist\refi-alpha\refi-alpha.exe
echo.
echo Para ejecutar:
echo   cd dist\refi-alpha
echo   refi-alpha.exe
