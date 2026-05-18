#!/bin/bash

# Script orquestador para generar paquetes eXe desde Unity Learn
# Uso: ./build_course.sh <csv_file> [course_slug]
# Ejemplo: ./build_course.sh data/UL_Unity_Essentials_6_0.csv unity_essentials

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${SCRIPT_DIR}/.venv/bin/python"

# Validar argumentos
if [ $# -lt 1 ]; then
    echo "Uso: $0 <csv_file> [course_slug]"
    echo "Ejemplo: $0 data/UL_Unity_Essentials_6_0.csv unity_essentials"
    exit 1
fi

CSV_FILE="$1"
COURSE_SLUG="${2:-}"

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
    --download-assets

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
    --output-dir "$EXE_OUTPUT"

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
