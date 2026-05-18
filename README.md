# UnityCourser

Automatiza la descarga y generación de paquetes eXe-compatible desde contenido de Unity Learn.

## ¿Qué hace?

1. **Descarga** HTML del curso desde un CSV de contenido
2. **Refresca** referencias a assets en el manifest.json
3. **Genera** paquete web estilo eXe listo para importar

## Estructura del Proyecto

```
UnityCourser/
├── scripts/                          # Scripts principales
│   ├── download_unity_learn.py      # Descarga HTML del curso
│   ├── refresh_manifest_assets.py   # Actualiza manifest.json
│   └── build_exe_web_from_manifest.py # Genera paquete eXe
├── data/                             # CSVs de entrada
├── downloads/                        # Contenido descargado (por curso)
├── elpx/                             # Paquetes ELPX generados
├── output/                           # Paquetes eXe generados
├── docs/                             # Documentación adicional
├── build_course.sh                   # Script orquestador (recomendado)
└── README.md
```

## Requisitos

- Python 3.10+
- Entorno virtual (`.venv`)

## Inicio Rápido

### Opción A: Script Orquestador (Recomendado)

```bash
./build_course.sh data/UL_Unity_Essentials_6_0.csv unity_essentials
```

Ejecuta los 3 pasos automáticamente. El slug se puede omitir (se genera del nombre del CSV).

### Opción B: Pasos Individuales

#### 1) Descargar contenido

```bash
.venv/bin/python scripts/download_unity_learn.py data/UL_Unity_Essentials_6_0.csv \
  --output-dir downloads/unity_essentials \
  --download-assets
```

#### 2) Refrescar manifest

```bash
.venv/bin/python scripts/refresh_manifest_assets.py \
  --manifest downloads/unity_essentials/manifest.json \
  --base-dir downloads/unity_essentials
```

#### 3) Generar paquete

```bash
.venv/bin/python scripts/build_exe_web_from_manifest.py \
  --manifest downloads/unity_essentials/manifest.json \
  --output-dir output/exe_unity_essentials
```

## Opciones del Build

### Mantener negritas (por defecto se eliminan)

```bash
.venv/bin/python scripts/build_exe_web_from_manifest.py \
  --manifest downloads/unity_essentials/manifest.json \
  --output-dir output/exe_unity_web \
  --keep-bold
```

### Copiar assets dentro del paquete

```bash
--copy-assets
```

## Opciones de Descarga

- `--limit 10` - Descargar solo primeros 10 items
- `--delay 1.5` - Pausa entre descargas (segundos)
- `--timeout 45` - Timeout por request
- `--overwrite` - Reemplazar HTML existentes

## Nota sobre Negritas

- **Por defecto**: se eliminan `<strong>` y `<b>` (mejora traducción automática)
- **Con `--keep-bold`**: se mantienen intactas
- La template se genera automáticamente si no existe

## Múltiples Cursos

Con el script orquestador es muy simple:

```bash
./build_course.sh data/CURSO_1.csv curso_1
./build_course.sh data/CURSO_2.csv curso_2
```

Cada curso genera:
- `downloads/curso_1/` - Contenido descargado
- `output/exe_curso_1/` - Paquete eXe
- `output/exe_curso_1.zip` - ZIP comprimido

## Troubleshooting

| Problema | Solución |
|----------|----------|
| Faltan recursos | Ejecuta `refresh_manifest_assets.py` antes del build |
| Caracteres especiales | Asegúrate que CSV esté en UTF-8 |

## Licencia

Creative Commons: Reconocimiento - compartir igual 4.0
