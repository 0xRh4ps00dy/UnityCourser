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
├── build_course.sh                   # Script orquestador (recomendado)
└── README.md
```

## Requisitos

- Python 3.10+
- Entorno virtual (`.venv`)

## Inicio Rápido

### Opción A: Script Orquestador (Recomendado)

**Uso básico:**

```bash
./build_course.sh data/UL_Unity_Essentials_6_0.csv unity_essentials
```

**Ejemplos con opciones:**

```bash
# Mantener negritas
./build_course.sh data/UL_Unity_Essentials_6_0.csv unity_essentials --keep-bold

# Copiar assets dentro del paquete
./build_course.sh data/UL_Unity_Essentials_6_0.csv unity_essentials --copy-assets

# Ambas opciones
./build_course.sh data/UL_Unity_Essentials_6_0.csv unity_essentials --keep-bold --copy-assets

# Descargar solo primeros 10 items
./build_course.sh data/UL_Unity_Essentials_6_0.csv unity_essentials --limit 10

# Pausa de 2 segundos entre descargas
./build_course.sh data/UL_Unity_Essentials_6_0.csv unity_essentials --delay 2

# Timeout de 60 segundos
./build_course.sh data/UL_Unity_Essentials_6_0.csv unity_essentials --timeout 60
```

El slug se puede omitir (se genera del nombre del archivo).

**Opciones disponibles:**

| Descarga | Build |
|----------|-------|
| `--limit N` | `--keep-bold` |
| `--delay N` | `--copy-assets` |
| `--timeout N` | |
| `--overwrite` | |

### Opción B: Pasos Individuales

#### 1) Descargar contenido

```bash
.venv/bin/python scripts/download_unity_learn.py data/UL_Unity_Essentials_6_0.csv \
  --output-dir downloads/unity_essentials \
  --download-assets \
  --limit 10 \
  --delay 2
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
  --output-dir output/exe_unity_essentials \
  --keep-bold \
  --copy-assets
```

## Opciones Importantes

### Negritas

Por defecto se **eliminan** `<strong>` y `<b>` (mejora traducción automática).

Con `--keep-bold` se mantienen intactas:

```bash
./build_course.sh data/UL_Unity_Essentials_6_0.csv unity_essentials --keep-bold
```

### Assets

Para copiar assets dentro del paquete eXe:

```bash
./build_course.sh data/UL_Unity_Essentials_6_0.csv unity_essentials --copy-assets
```

### Descarga

- `--limit 10` - Solo primeros 10 items (testing)
- `--delay 2` - Pausa entre descargas
- `--timeout 60` - Timeout por request
- `--overwrite` - Reemplazar HTML existentes

### Notas Técnicas

- **Template**: Se genera automáticamente si no existe
- **ZIP**: Se crea automáticamente en `output/`
- Orden de ejecución: Descarga → Refresco → Build

## Múltiples Cursos

```bash
./build_course.sh data/CURSO_1.csv curso_1 --keep-bold
./build_course.sh data/CURSO_2.csv curso_2
```

Cada curso genera:
- `downloads/curso_X/` - Contenido descargado
- `output/exe_curso_X/` - Paquete eXe
- `output/exe_curso_X.zip` - ZIP comprimido

## Troubleshooting

| Problema | Solución |
|----------|----------|
| Faltan recursos | Ejecuta `refresh_manifest_assets.py` antes del build |
| Caracteres especiales | Asegúrate que CSV esté en UTF-8 |

## Licencia

Creative Commons: Reconocimiento - compartir igual 4.0
