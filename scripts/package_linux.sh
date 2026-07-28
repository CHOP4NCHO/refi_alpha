#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Evitar /tmp (tmpfs con cuota limitada) para staging de fpm
TMPDIR="$PROJECT_ROOT/.tmp"
mkdir -p "$TMPDIR"
export TMPDIR

FORMAT="${1:-all}"

# Validar formato
if [[ "$FORMAT" != "deb" && "$FORMAT" != "rpm" && "$FORMAT" != "all" ]]; then
    echo "ERROR: Formato no valido: $FORMAT"
    echo "Uso: $0 [deb|rpm|all]"
    exit 1
fi

# Validar build de PyInstaller
BUILD_DIR="$PROJECT_ROOT/dist/refi-alpha"
EXECUTABLE="$BUILD_DIR/refi-alpha"

if [ ! -f "$EXECUTABLE" ]; then
    echo "ERROR: No se encontro el ejecutable: $EXECUTABLE"
    echo "Ejecuta primero: ./build.sh"
    exit 1
fi

# Validar fpm
if ! command -v fpm &> /dev/null; then
    echo "ERROR: fpm no esta instalado."
    echo "Debe instalarse antes de continuar."
    echo ""
    echo "Instalacion rapida (Ruby + fpm):"
    echo "  sudo apt-get install ruby ruby-dev rubygems build-essential  # Debian/Ubuntu"
    echo "  sudo gem install --no-document fpm"
    echo ""
    echo "O consulta: https://fpm.readthedocs.io/en/latest/installing.html"
    exit 1
fi

# Obtener version desde git
if [ -d "$PROJECT_ROOT/.git" ]; then
    VERSION=$(cd "$PROJECT_ROOT" && git describe --tags --always 2>/dev/null || echo "0.0.0")
else
    VERSION="0.0.0"
fi

echo "=== REFI ALPHA - Empaquetado Linux ==="
echo "Version detectada: $VERSION"
echo "Formato solicitado: $FORMAT"
echo ""

# Preparar estructura del paquete
PACKAGE_ROOT="$PROJECT_ROOT/package-root"
rm -rf "$PACKAGE_ROOT"
mkdir -p "$PACKAGE_ROOT/opt/refi-alpha"
mkdir -p "$PACKAGE_ROOT/usr/share/applications"
mkdir -p "$PACKAGE_ROOT/usr/share/pixmaps"

# Copiar contenido del build
cp -r "$BUILD_DIR"/* "$PACKAGE_ROOT/opt/refi-alpha/"

# Copiar desktop entry
DESKTOP_SRC="$PROJECT_ROOT/package-assets/refi-alpha.desktop"
if [ ! -f "$DESKTOP_SRC" ]; then
    echo "ERROR: No se encontro el desktop entry: $DESKTOP_SRC"
    exit 1
fi
cp "$DESKTOP_SRC" "$PACKAGE_ROOT/usr/share/applications/refi-alpha.desktop"

# Copiar icono
ICON_SRC="$PROJECT_ROOT/ui_pyqt/refi.png"
if [ ! -f "$ICON_SRC" ]; then
    echo "ERROR: No se encontro el icono: $ICON_SRC"
    exit 1
fi
cp "$ICON_SRC" "$PACKAGE_ROOT/usr/share/pixmaps/refi-alpha.png"

# Asegurar directorio de salida
PACKAGES_DIR="$PROJECT_ROOT/packages"
mkdir -p "$PACKAGES_DIR"

echo "Generando paquetes en: $PACKAGES_DIR"
echo ""

# Generar .deb
if [[ "$FORMAT" == "deb" || "$FORMAT" == "all" ]]; then
    echo "Generando paquete Debian (.deb)..."
    fpm \
        -s dir \
        -t deb \
        -n refi-alpha \
        -v "$VERSION" \
        --architecture amd64 \
        --prefix / \
        --description "REFI Alpha - Evaluador de fidelidad de requisitos" \
        --url "https://github.com/refi-alpha" \
        --maintainer "REFI Alpha Team" \
        -C "$PACKAGE_ROOT" \
        .
    mv "${PROJECT_ROOT}/refi-alpha_${VERSION}_amd64.deb" "$PACKAGES_DIR/"
    echo "OK: $PACKAGES_DIR/refi-alpha_${VERSION}_amd64.deb"
fi

# Generar .rpm
if [[ "$FORMAT" == "rpm" || "$FORMAT" == "all" ]]; then
    echo "Generando paquete RPM (.rpm)..."
    fpm \
        -s dir \
        -t rpm \
        -n refi-alpha\
        -v "$VERSION" \
        --architecture x86_64 \
        --prefix / \
        --description "REFI Alpha - Evaluador de fidelidad de requisitos" \
        --url "https://github.com/CHOP4NCHO/refi_alpha" \
        --maintainer "CHOP4NCHO" \
        -C "$PACKAGE_ROOT" \
        .
    mv "${PROJECT_ROOT}/refi-alpha-${VERSION}-1.x86_64.rpm" "$PACKAGES_DIR/"
    echo "OK: $PACKAGES_DIR/refi-alpha-${VERSION}-1.x86_64.rpm"
fi

echo ""
echo "=== Empaquetado completado ==="
echo "Paquetes generados en: $PACKAGES_DIR"
