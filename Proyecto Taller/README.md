# PyEPH.AR

Aplicación de análisis y visualización de la Encuesta Permanente de Hogares
(EPH) del INDEC, desarrollada para el Taller de Lenguajes (Redictado 2026).

## Integrantes

1. Lucas Pascual Martina
2. Felipe Marín Russo
3. Lautaro Agustín López
4. Gonzalo Ariel Escribano Echever

## Descripción

El proyecto procesa los microdatos de la EPH de dos categorías:

- **Mercado Laboral** (archivos de hogares e individuos, por trimestre).
- **Ciencia y Tecnología** (módulo de tecnologías de la información y la
  comunicación, por año).

Qué hace hoy (primera etapa, solo con el módulo `csv` de Python):

| Parte | Qué calcula | Dónde |
|---|---|---|
| A.1 | Completitud (valores faltantes) de hogares e individuos, con umbrales de 5%, 10% y 20% | `notebooks/hogares_mercado_laboral.ipynb`, `notebooks/individuos_mercado_laboral.ipynb` |
| A.2 y A.3 | Inconsistencias con las etiquetas CRÍTICO, ERROR, VERIFICAR, ADVERTENCIA e INFO, e informes por rol (docente, investigador, analista) | `notebooks/individuos_mercado_laboral.ipynb` |
| B.1 | Tasa de desempleo y distribución de la población por aglomerado, por sexo y rango etario, por trimestre, semestre y año | `notebooks/individuos_mercado_laboral.ipynb` |
| C | Consistencia de archivos y porcentaje de hogares con celular, internet y computadora por región y aglomerado | `notebooks/ciencia_tecnologia.ipynb` |

Los informes se guardan como JSON en `output/`.

## Requisitos

- Python 3.9 o superior (probado con 3.12).
- Funciona en Windows, Linux y macOS.

## Instalación

```bash
# 1. Crear y activar un entorno virtual
python -m venv .venv
# Windows:      .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate

# 2. Instalar las librerías
pip install -r requirements.txt
```

## Dónde van los datos

Los archivos de la EPH **no están dentro del proyecto**. Van en una carpeta
llamada `files`, que debe estar **al lado** de la carpeta del proyecto:

```
mi_carpeta/
├── files/                          <- datos (se descargan del INDEC)
│   ├── mercado_laboral/            <- hogares e individuos, tal como se descomprimen
│   └── ciencia_y_tecnologia/       <- hogares e individuos de tecnología
└── proyecto_taller/                <- este repositorio
```

- Los archivos se dejan **como se descomprimen**: no hace falta ordenarlos por
  año. El programa detecta solo la categoría (por la carpeta) y el tipo, el año
  y el trimestre (por el nombre, por ejemplo `usu_hogar_T124.txt`).
- **Agregar un año:** copiar sus archivos en la carpeta de la categoría. No se
  modifica el código.
- **Agregar una categoría:** crear una carpeta nueva dentro de `files/`.
- Para cambiar la ubicación de los datos se modifica una sola línea:
  `DIR_DATOS` en `src/config.py`.

Descarga: https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos-1

## Cómo ejecutarlo

Desde la carpeta del proyecto:

```bash
jupyter notebook
```

Abrir y ejecutar todas las celdas (en este orden recomendado):

1. `notebooks/hogares_mercado_laboral.ipynb`
2. `notebooks/individuos_mercado_laboral.ipynb` (al final pide años y
   aglomerados por teclado; si no se escribe nada se usan valores por defecto)
3. `notebooks/ciencia_tecnologia.ipynb`

## Estructura del proyecto

```
proyecto_taller/
├── src/
│   ├── config.py        <- todos los criterios que pueden cambiar
│   ├── rutas.py         <- raíz del proyecto
│   ├── data_loader.py   <- leer, detectar y filtrar archivos; guardar JSON
│   ├── profiling.py     <- completitud (A.1), consistencia (A.2, A.3) y roles
│   ├── tendencias.py    <- tendencias por aglomerado (B.1)
│   └── tecnologia.py    <- consistencia y penetración tecnológica (C)
├── notebooks/           <- los tres notebooks
├── output/              <- informes JSON generados
├── bitacora.md          <- decisiones, problemas y consultas
├── requirements.txt
├── LICENSE
└── README.md
```

## Cómo cambiar los criterios de análisis

Todo se configura en `src/config.py`, sin tocar las funciones:

| Quiero cambiar | Constante |
|---|---|
| Carpeta de los datos | `DIR_DATOS` |
| Umbrales de faltantes | `UMBRALES_FALTANTES_PCT` |
| Variables analizadas | `VARS_INDIVIDUOS_*`, `VARS_HOGARES_*` |
| Qué cuenta como faltante | `FALTANTES_REALES`, `NO_CORRESPONDE` |
| Edades de las reglas | `EDAD_MIN_ERROR`, `EDAD_MAX_ERROR`, `EDAD_MIN_VERIFICAR`, `EDAD_LEGAL_TRABAJO`, `EDAD_MIN_UNIVERSITARIO`, `EDAD_MIN_JUBILACION_POR_SEXO` |
| Roles | `ROLES` |
| Rangos etarios y semestres | `RANGOS_ETARIOS`, `SEMESTRES` |
| Qué hacer si el informe de tecnología ya existe | `MODO_ARCHIVO_EXISTENTE` |

## Estilo

El código sigue PEP 8 y todas las funciones tienen docstrings:

```bash
python -m pycodestyle src
```

## Estado

- Primera etapa: implementada (partes A, B y C). 
- Aplicación Streamlit y análisis con pandas: segunda etapa.

## Licencia

MIT (ver `LICENSE`).

*----------------------------------------------*

# PyEPH.AR pt2


# Cómo se ejecuta

1. Instalar las dependencias (ver "Instalación" más arriba).
2. Verificar que la carpeta `files` con los datos de la EPH esté **al lado**
   de la carpeta del proyecto (ver "Dónde van los datos").
3. Abrir una terminal **en la carpeta raíz del proyecto** (la que contiene
   `src/`, `streamlit/` y `README.md`) y ejecutar:

bash
streamlit run streamlit/app.py


4. Se abre el navegador en `http://localhost:8501`. Si hace falta, seguir el
   tutorial de la página de inicio.

# descripción breve del proyecto

  Este proyecto es la continuación de la entrega pasada. Se busca mostrar la información de
  los datos ya analizados, con gráficos, métricas y mapas, denrto de un entorno interactivo.