# UnityCourser

Automatiza la descarga de contenido de Unity Learn desde CSV y genera un paquete web compatible con eXeLearning (incluyendo ZIP final para importar).

## Que hace este proyecto

- Lee un CSV de curso exportado (titulo, URL, tipo, duracion, resumen).
- Descarga las paginas HTML del curso y las organiza por mision.
- Detecta y refresca recursos (assets) en el `manifest.json`.
- Genera un paquete estilo eXe en una carpeta de salida.
- Crea automaticamente un archivo `.zip` listo para probar/importar.

## Scripts principales

- `download_unity_learn.py`: descarga HTML del curso desde CSV y opcionalmente assets.
- `refresh_manifest_assets.py`: reconstruye el bloque `assets` del manifest segun archivos locales.
- `build_exe_web_from_manifest.py`: genera el paquete web eXe y el ZIP final.

Nota: El bloque de `iframe` de "Contenido web original" fue eliminado del generador para evitar cuadros negros con `not found`.

## Requisitos

- Linux/macOS/Windows con Python 3.10+
- Entorno virtual en `.venv`

Si ya tienes `.venv`, usa siempre el interprete del entorno:

```bash
/media/rh4ps00dy/Data/UnityCourser/.venv/bin/python
```

## Flujo completo (un curso)

Ejemplo usando:

- CSV: `UL_Unity_Essentials_6_0.csv`
- slug del curso: `unity_essentials`

### 1) Descargar HTML (y assets opcionalmente)

```bash
/media/rh4ps00dy/Data/UnityCourser/.venv/bin/python download_unity_learn.py UL_Unity_Essentials_6_0.csv \
  --output-dir downloads/unity_essentials \
  --download-assets
```

Opciones utiles:

- `--limit 10`: baja solo los primeros 10 items.
- `--delay 1.5`: pausa entre descargas.
- `--timeout 45`: timeout por request.
- `--overwrite`: reemplaza HTML existentes.

### 2) Refrescar manifest de assets

```bash
/media/rh4ps00dy/Data/UnityCourser/.venv/bin/python refresh_manifest_assets.py \
  --manifest downloads/unity_essentials/manifest.json \
  --base-dir downloads/unity_essentials
```

### 3) Generar paquete eXe y ZIP

```bash
/media/rh4ps00dy/Data/UnityCourser/.venv/bin/python build_exe_web_from_manifest.py \
  --manifest downloads/unity_essentials/manifest.json \
  --output-dir exe_unity_web
```

Salida esperada:

- Carpeta del paquete: `exe_unity_web/`
- ZIP final: `exe_unity_web.zip`

## Repetir con otros cursos (otros CSV)

Para escalar a multiples cursos, usa un slug distinto por curso y no mezcles salidas.

Ejemplo para otro CSV:

```bash
# 1) Descargar
/media/rh4ps00dy/Data/UnityCourser/.venv/bin/python download_unity_learn.py MI_OTRO_CURSO.csv \
  --output-dir downloads/mi_otro_curso \
  --download-assets

# 2) Refrescar manifest
/media/rh4ps00dy/Data/UnityCourser/.venv/bin/python refresh_manifest_assets.py \
  --manifest downloads/mi_otro_curso/manifest.json \
  --base-dir downloads/mi_otro_curso

# 3) Build paquete + zip
/media/rh4ps00dy/Data/UnityCourser/.venv/bin/python build_exe_web_from_manifest.py \
  --manifest downloads/mi_otro_curso/manifest.json \
  --output-dir exe_mi_otro_curso
```

Resultado de ese curso:

- `exe_mi_otro_curso/`
- `exe_mi_otro_curso.zip`

## Estructura recomendada para multiples cursos

```text
UnityCourser/
  downloads/
    unity_essentials/
    mi_otro_curso/
  exe_unity_web/
  exe_unity_web.zip
  exe_mi_otro_curso/
  exe_mi_otro_curso.zip
```

## Comandos rapidos

Regenerar solo el ZIP de un curso ya descargado:

```bash
/media/rh4ps00dy/Data/UnityCourser/.venv/bin/python build_exe_web_from_manifest.py \
  --manifest downloads/unity_essentials/manifest.json \
  --output-dir exe_unity_web
```

## Solucion de problemas

- Si faltan recursos en salida:
  - Ejecuta `refresh_manifest_assets.py` antes del build.
- Si cambiaste el generador:
  - Ejecuta de nuevo `build_exe_web_from_manifest.py` para regenerar HTML y ZIP.
- Si quieres conservar assets dentro del paquete eXe:
  - Usa `--copy-assets` al generar el build.

Ejemplo:

```bash
/media/rh4ps00dy/Data/UnityCourser/.venv/bin/python build_exe_web_from_manifest.py \
  --manifest downloads/unity_essentials/manifest.json \
  --output-dir exe_unity_web \
  --copy-assets
```

## Siguiente mejora sugerida

Crear un script orquestador (por ejemplo `build_course.sh`) para ejecutar los 3 pasos con un solo comando:

```bash
./build_course.sh UL_Unity_Essentials_6_0.csv unity_essentials
```
