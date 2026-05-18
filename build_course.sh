#!/bin/bash

# Script orquestador para generar paquetes eXe desde Unity Learn
# Uso: ./build_course.sh <csv_file> [course_slug] [opciones]
# Ejemplo: ./build_course.sh data/UL_Unity_Essentials_6_0.csv unity_essentials --keep-bold
# 
# Opciones de descarga:
#   --limit N           Descargar solo primeros N items
#   --delay SEGUNDOS    Pausa entre descargas
#   --timeout SEGUNDOS  Timeout por request
#   --overwrite         Reemplazar HTML existentes
#
# Opciones de build:
#   --keep-bold         Mantener negritas (por defecto se eliminan)
#   --copy-assets       Copiar assets dentro del paquete

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${SCRIPT_DIR}/.venv/bin/python"

# Validar argumentos
if [ $# -lt 1 ]; then
    echo "Uso: $0 <csv_file> [course_slug] [opciones]"
    echo ""
    echo "Ejemplo: $0 data/UL_Unity_Essentials_6_0.csv unity_essentials --keep-bold"
    echo ""
    echo "Opciones de descarga:"
    echo "  --limit N           Descargar solo primeros N items"
    echo "  --delay SEGUNDOS    Pausa entre descargas"
    echo "  --timeout SEGUNDOS  Timeout por request"
    echo "  --overwrite         Reemplazar HTML existentes"
    echo ""
    echo "Opciones de build:"
    echo "  --keep-bold         Mantener negritas (por defecto se eliminan)"
    echo "  --copy-assets       Copiar assets dentro del paquete"
    exit 1
fi

CSV_FILE="$1"
COURSE_SLUG="${2:-}"
shift 2 2>/dev/null || true

# Validar que exista el archivo CSV
if [ ! -f "$CSV_FILE" ]; then
    echo "❌ Error: Archivo CSV no encontrado: $CSV_FILE"
    exit 1
fi

# Si no se proporciona slug, generar desde nombre del archivo
if [ -z "$COURSE_SLUG" ]; then
    BASENAME=$(basename "$CSV_FILE" .csv)
    # Convertir a minúsculas y reemplazar guiones/espacios
    COURSE_SLUG=$(echo "$BASENAME" | tr '[:upper:]' '[:lower:]' | sed 's/_/-/g' | sed 's/ul-//' | sed 's/6-0//')
    echo "ℹ️  Slug generado: $COURSE_SLUG"
fi

# Separar opciones por destino
DOWNLOAD_OPTS=""
BUILD_OPTS=""

while [ $# -gt 0 ]; do
    case "$1" in
        --limit|--delay|--timeout)
            DOWNLOAD_OPTS="$DOWNLOAD_OPTS $1 $2"
            shift 2
            ;;
        --overwrite)
            DOWNLOAD_OPTS="$DOWNLOAD_OPTS $1"
            shift
            ;;
        --keep-bold|--copy-assets)
            BUILD_OPTS="$BUILD_OPTS $1"
            shift
            ;;
        *)
            echo "❌ Opción desconocida: $1"
            exit 1
            ;;
    esac
done

OUTPUT_DIR="downloads/$COURSE_SLUG"
MANIFEST="$OUTPUT_DIR/manifest.json"
EXE_OUTPUT="output/exe_$COURSE_SLUG"

echo "═══════════════════════════════════════════════════════════"
echo "🚀 Generando paquete eXe para: $COURSE_SLUG"
echo "═══════════════════════════════════════════════════════════"

# Paso 1: Descargar
echo ""
echo "📥 Paso 1: Descargando contenido..."
echo "────────────────────────────────────────────────────────────"
$PYTHON scripts/download_unity_learn.py "$CSV_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --download-assets \
    $DOWNLOAD_OPTS

if [ ! -f "$MANIFEST" ]; then
    echo "❌ Error: manifest.json no fue creado"
    exit 1
fi

echo "✅ Descarga completada"

# Paso 2: Refrescar manifest
echo ""
echo "🔄 Paso 2: Refrescando manifest de assets..."
echo "────────────────────────────────────────────────────────────"
$PYTHON scripts/refresh_manifest_assets.py \
    --manifest "$MANIFEST" \
    --base-dir "$OUTPUT_DIR"

echo "✅ Manifest refrescado"

# Paso 3: Generar paquete eXe
echo ""
echo "🏗️  Paso 3: Generando paquete eXe..."
echo "────────────────────────────────────────────────────────────"
$PYTHON scripts/build_exe_web_from_manifest.py \
    --manifest "$MANIFEST" \
    --output-dir "$EXE_OUTPUT" \
    $BUILD_OPTS

if [ ! -d "$EXE_OUTPUT" ]; then
    echo "❌ Error: Paquete no fue generado"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ ¡Éxito! Paquete generado:"
echo ""
echo "   📁 Carpeta: $EXE_OUTPUT"
echo "   📦 ZIP:     $EXE_OUTPUT.zip"
echo "═══════════════════════════════════════════════════════════"
echo ""
