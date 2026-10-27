"""Configuración central.
 
Acá viven los datos y criterios del proyecto que pueden cambiar: rutas,
parámetros de lectura de archivos, definición de valores faltantes,
umbrales y listas de variables a analizar. La lógica del análisis no va
en este archivo: si cambia un criterio, se modifica acá y las funciones
no se tocan.
"""
from src import rutas
from pathlib import Path

# =============================================================================
# RUTAS
# =============================================================================
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

def obtener_ruta_del_dataset(data,carpeta,dataset):

    """
    es una funcion que devuelve la ruta del dataset
    """

    ruta_completa = RAIZ_PROYECTO / data / carpeta  / dataset 
    return str(ruta_completa)


# Carpeta raíz donde viven las categorías (files/mercado_laboral, etc.).
DIR_DATOS = rutas.RAIZ_PROYECTO.parent / "files"
# Carpeta donde se guardan los informes generados.
DIR_SALIDA = rutas.RAIZ_PROYECTO / "output"
# Reporte JSON de calidad de datos (se va completando por requerimiento).
RUTA_REPORTE = DIR_SALIDA / "calidad_datos.json"
# Un archivo por umbral de faltantes (Modificación 4).
# {umbral} se reemplaza por el porcentaje.
ARCHIVO_CALIDAD = "calidad_datos_umbral_{umbral}.json"

# =============================================================================
# LECTURA DE ARCHIVOS
# =============================================================================
SEPARADOR = ";"
# Se indica el encoding de forma explícita.
ENCODING = "utf-8"

# =============================================================================
# DETECCIÓN AUTOMÁTICA DE ARCHIVOS
# =============================================================================
# Los archivos se dejan tal como se descomprimen,
# así que tipo, año y trimestre se obtienen del NOMBRE del archivo.
TIPO_HOGAR = "hogar"
TIPO_INDIVIDUO = "individual"
# Palabras que, si aparecen en el nombre del archivo, identifican el tipo.
CLAVES_TIPO = {
    TIPO_HOGAR: ("hogar", "hog"),
    TIPO_INDIVIDUO: ("individual", "indiv"),
}

# Trimestres que debe tener un año completo de Mercado Laboral. Es para
# chequear que no falte ningún archivo (data_loader.trimestres_faltantes).
TRIMESTRES = ("T1", "T2", "T3", "T4")

# Nombres de las carpetas de categoría dentro de la carpeta de datos.
CAT_MERCADO_LABORAL = "mercado_laboral"
CAT_CIENCIA_TECNOLOGIA = "ciencia_y_tecnologia"

# =============================================================================
# VALORES FALTANTES (Requerimiento A.1)
# =============================================================================
# Se distinguen dos tipos de valor, que se informan por separado:
#   - faltante real: la persona/hogar debía responder y no hay dato.
#   - no corresponde: la pregunta no aplica; no es un problema de calidad.
#
# Todos los valores son texto, porque los archivos se leen como texto.
# Un código de un solo elemento lleva coma final, ("-9",), para que sea una
# tupla y no un texto entre paréntesis.
#
# ORDEN DE CONSULTA: NO_CORRESPONDE tiene prioridad sobre VALOR_VACIO. Hay
# columnas donde el vacío significa "no corresponde" (ver PP04D_COD).
 
# Un campo vacío es faltante real en CUALQUIER columna, salvo que la columna
# figure en NO_CORRESPONDE con el vacío como código.
VALOR_VACIO = ""

# Código de estado: entrevista individual no realizada.
ESTADO_NO_REALIZADA = "0"

# Código de no respuesta en montos de ingreso (Anexo I).
INGRESO_NO_RESPUESTA = "-9"

# Códigos de "no respondió", solo en las columnas indicadas.
FALTANTES_REALES = {
    # Diseño de registro EPH, Anexo I: en los montos de ingreso la no
    # respuesta se codifica como -9.
    "P47T": ("-9",),
    "P21": ("-9",),
    # Un 0 en ITF/IPCF se interpreta como "no responde".
    # Evidencia (T1 2024): el 97,6% de esos hogares tiene DECIFR = 12
    # (no respuesta de ingresos); el 2,4% restante tiene DECIFR = 0.
    "ITF": ("0",),
    "IPCF": ("0",),
    # ESTADO = 0 es "entrevista individual no realizada": a esa persona le
    # correspondía responder y no hay dato (55 a 81 casos por trimestre).
    "ESTADO": ("0",),
    # Anexo I: el código 9 es "no sabe / no responde".
    "CAT_OCUP": ("9",),
    "NIVEL_ED": ("9",),
    "CH08": ("9",),
    # Decil 12 = "no respuesta de ingresos"; 13 = entrevista individual no
    # realizada.
    "IDECIFR": ("12", "13"),
    # En las preguntas de ciencia y tecnología, el código 9 significa "no
    # sabe / no responde".
    "IH_II_01": ("9",),
    "IH_II_02": ("9",),
    "IP_III_04": ("9",),
    "IP_III_05": ("9",),
    "IP_III_06": ("9",),
}

# Códigos de "la pregunta no corresponde", solo en las columnas indicadas.
# Desde T3 2024 INDEC cambió el formato: en T1 y T2 el "no corresponde" viene
# como campo VACÍO y desde T3 como el texto "NA". Se aceptan los dos para que
# los trimestres sean comparables.
NO_CORRESPONDE = {
    # Código de ocupación: solo aplica a ocupados (todos los ocupados tienen
    # código en los 4 trimestres).
    "PP04D_COD": (VALOR_VACIO, "NA"),
    # Decil "del interior": no aplica a los aglomerados 32 y 33 (GBA).
    "IDECIFR": (VALOR_VACIO, "NA"),
    # Solo se completa si CH16 es 3, 4 o 5 (vivía en otra provincia o país).
    "CH16_COD": (VALOR_VACIO, "NA"),
    # Marca de caso imputado: 1 = imputado; vacío/NA = no imputado.
    "IMPUTA": (VALOR_VACIO, "NA"),
    # El 0 significa que la secuencia no corresponde (Anexo I).
    "CAT_OCUP": ("0",),
    "CAT_INAC": ("0",),
}

# Notas que se agregan al informe para las columnas que las tienen. Explican
# casos que no se pueden expresar con los diccionarios de arriba.
NOTAS_COLUMNAS = {
    "GDECCFR": (
        "Decil de ingreso per cápita familiar de los aglomerados de 500.000 "
        "o más habitantes: está vacío cuando MAS_500 = N, por lo que ese "
        "faltante no es un problema de calidad (la pregunta no "
        "corresponde). Se informa el valor sin ajustar para que sea "
        "comparable con otros grupos."
    ),
    "ITF": (
        "Un 0 se interpreta como 'no responde' (decisión del grupo). "
        "Evidencia: el 97,6% de esos hogares tiene DECIFR = 12."
    ),
    "P47T": "El 0 se considera un dato válido (persona sin ingresos).",
}

# =============================================================================
# ANÁLISIS DE COMPLETITUD (Requerimiento A.1, Modificaciones 2, 3 y 4)
# =============================================================================
# Umbral por defecto: se informan las columnas con MÁS de este porcentaje de
# faltantes.
UMBRAL_FALTANTES_PCT = 5.0
# Umbrales a comparar (Modificación 4): se genera un informe por cada uno.
UMBRALES_FALTANTES_PCT = (5, 10, 20)

# Individuos: pedidas por el enunciado + 2 del grupo + las del anexo.
VARS_INDIVIDUOS_OBLIGATORIAS = ["PONDERA", "AGLOMERADO", "REGION", "ESTADO"]
VARS_INDIVIDUOS_EXTRA = ["PP04D_COD", "P47T"]
VARS_INDIVIDUOS_ANEXO = [
    "CH06", "CH08", "IDECIFR", "CAT_INAC", "CAT_OCUP", "NIVEL_ED",
    "ANO4", "TRIMESTRE", "CH16_COD", "IMPUTA",
]
VARS_INDIVIDUOS = (VARS_INDIVIDUOS_OBLIGATORIAS + VARS_INDIVIDUOS_EXTRA
                   + VARS_INDIVIDUOS_ANEXO)

# Hogares: pedidas por el enunciado + 2 del grupo + las del anexo.
VARS_HOGARES_OBLIGATORIAS = ["ANO4", "TRIMESTRE", "ITF", "MAS_500", "GDECCFR"]
VARS_HOGARES_EXTRA = ["REALIZADA", "IV1"]
VARS_HOGARES_ANEXO = ["CODUSU", "PONDERA", "AGLOMERADO", "REGION"]
VARS_HOGARES = (VARS_HOGARES_OBLIGATORIAS + VARS_HOGARES_EXTRA
                + VARS_HOGARES_ANEXO)

# =============================================================================
# CONSTANTES (Requerimientos A.2 y A.3)
# =============================================================================
ETIQUETA_ERROR = "ERROR"
ETIQUETA_VERIFICAR = "VERIFICAR"

# Columnas usadas por las reglas.
COL_EDAD = "CH06"
COL_ESTADO = "ESTADO"
COL_CAT_OCUP = "CAT_OCUP"
COL_CAT_INAC = "CAT_INAC"
# Ingreso de la ocupación principal.
COL_INGRESO = "P21"

# Códigos de ESTADO.
ESTADO_OCUPADO = "1"
ESTADO_DESOCUPADO = "2"
ESTADO_INACTIVO = "3"
ESTADO_MENOR_10 = "4"
# Estados que cuentan como "activo" (trabaja o busca trabajo).
ESTADOS_ACTIVOS = (ESTADO_OCUPADO, ESTADO_DESOCUPADO)

# Códigos de CAT_OCUP.
CAT_OCUP_ACTIVAS = ("1", "2", "3", "4")
CAT_OCUP_NSNR = "9"

# Consistencia edad-trabajo: rangos de edad.
EDAD_MIN_ERROR = 10
EDAD_MAX_ERROR = 14
EDAD_MIN_VERIFICAR = 80
EXTREMOS_INCLUIDOS = True

# Consistencia edad-trabajo: criterios propios del grupo.
# Edad legal para empezar a trabajar en Argentina (Ley 26.390). Un ocupado
# entre EDAD_MAX_ERROR y esta edad se informa para VERIFICAR.
EDAD_LEGAL_TRABAJO = 16
# Un jubilado/pensionado menor a esta edad se informa para VERIFICAR (puede
# ser una pensión por fallecimiento de un familiar, por eso no es ERROR).
EDAD_MIN_JUBILADO = 30
CAT_INAC_JUBILADO = "1"

# Reporte: identificación de la persona y cantidad de ejemplos por criterio.
COLS_IDENTIFICACION = ("CODUSU", "NRO_HOGAR", "COMPONENTE", "AGLOMERADO")
COLS_PERIODO = ("ANO4", "TRIMESTRE")
MAX_EJEMPLOS = 5


# --- Etiquetas nuevas (Modificación 5.3) ---------------------------------
# Criterios:
#   CRÍTICO: invalida el registro o la columna; se recomienda no usarlo.
#   ERROR: contradicción lógica entre variables, sin ambigüedad.
#   VERIFICAR: caso raro que puede ser legítimo; requiere revisión humana.
#   ADVERTENCIA: situación inusual pero posible (outlier, valor raro).
#   INFO: observación para documentar; no es una inconsistencia.
ETIQUETA_CRITICO = "CRÍTICO"
ETIQUETA_ADVERTENCIA = "ADVERTENCIA"
ETIQUETA_INFO = "INFO"
# De mayor a menor gravedad (ordena los informes).
ORDEN_ETIQUETAS = (
    ETIQUETA_CRITICO,
    ETIQUETA_ERROR,
    ETIQUETA_VERIFICAR,
    ETIQUETA_ADVERTENCIA,
    ETIQUETA_INFO,
)
# Etiquetas que cuentan como "inconsistencia" en el informe por roles.
ETIQUETAS_INCONSISTENCIA = (
    ETIQUETA_CRITICO,
    ETIQUETA_ERROR,
    ETIQUETA_VERIFICAR,
)
 
# --- Columnas --------------------------------------------------------------
COL_PONDERA = "PONDERA"
COL_AGLOMERADO = "AGLOMERADO"
COL_SEXO = "CH04"
COL_NIVEL_ED = "NIVEL_ED"
COL_INGRESO_TOTAL = "P47T"       # ingreso total individual
COL_INGRESO_OTRAS = "TOT_P12"    # ingreso de otras ocupaciones
COL_ITF = "ITF"                  # ingreso total familiar
 
# --- Sexo (CH04) -----------------------------------------------------------
SEXO_VARON = "1"
SEXO_MUJER = "2"
NOMBRES_SEXO = {SEXO_VARON: "Varón", SEXO_MUJER: "Mujer"}
 
# --- Modificación 5: nuevas reglas de A.3 ----------------------------------
# NIVEL_ED: 5 = superior universitario incompleto, 6 = completo.
NIVEL_ED_UNIVERSITARIO = ("5", "6")
# Edad mínima para tener nivel universitario (se cambia SOLO acá).
EDAD_MIN_UNIVERSITARIO = 14
# Edad mínima de jubilación según sexo (Ley 24.241: varones 65, mujeres 60).
# Si en el futuro se unifican, se pone el mismo número en las dos entradas.
EDAD_MIN_JUBILACION_POR_SEXO = {SEXO_VARON: 65, SEXO_MUJER: 60}
# Una persona de esta edad o más se informa como ADVERTENCIA (valor raro).
EDAD_OUTLIER = 100
# El trabajador familiar sin remuneración puede legítimamente no cobrar.
CAT_OCUP_TRABAJADOR_FAMILIAR = "4"
 
# --- Modificación 5.4: roles -----------------------------------------------
# Cada rol define las columnas de las que quiere saber si tienen
# inconsistencias.
# Para agregar un rol nuevo alcanza con agregar una entrada.
ROLES = {
    "docente": ["ESTADO", "CAT_OCUP", "NIVEL_ED"],
    "investigador": ["ESTADO", "ITF", "CH06"],
    "analista": ["ESTADO", "CAT_OCUP", "ITF", "CH06", "NIVEL_ED"],
}
ARCHIVO_ROLES = "calidad_datos_roles.json"
 
# --- Parte B (B.1) ---------------------------------------------------------
# Población sobre la que se calcula la distribución: ocupados, desocupados e
# inactivos. Quedan afuera ESTADO = 0 (sin entrevista) y ESTADO = 4 (menores
# de 10 años).
ESTADOS_DISTRIBUCION = (ESTADO_OCUPADO, ESTADO_DESOCUPADO, ESTADO_INACTIVO)
# Nombre con el que cada estado aparece en el informe.
NOMBRES_ESTADO = {
    ESTADO_OCUPADO: "ocupados",
    ESTADO_DESOCUPADO: "desocupados",
    ESTADO_INACTIVO: "inactivos",
}
# Grupo para las personas cuya edad no entra en ningún rango etario.
RANGO_SIN_EDAD = "sin edad válida"

# (nombre, edad mínima, edad máxima); máxima None = sin límite superior.
RANGOS_ETARIOS = (
    ("10 a 14", 10, 14),
    ("15 a 24", 15, 24),
    ("25 a 34", 25, 34),
    ("35 a 44", 35, 44),
    ("45 a 64", 45, 64),
    ("65 y más", 65, None),
)

# Semestres: trimestres que incluye cada uno.
SEMESTRES = {"S1": ("T1", "T2"), "S2": ("T3", "T4")}

ARCHIVO_TENDENCIAS_TRIMESTRAL = "tendencias_trimestral.json"
ARCHIVO_TENDENCIAS_PERIODOS = "tendencias_semestral_anual.json"

# Código de aglomerado -> nombre (Diseño de registro EPH), sin cero inicial.
AGLOMERADOS = {
    "2": "Gran La Plata",
    "3": "Bahía Blanca-Cerri",
    "4": "Gran Rosario",
    "5": "Gran Santa Fe",
    "6": "Gran Paraná",
    "7": "Posadas",
    "8": "Gran Resistencia",
    "9": "Comodoro Rivadavia-Rada Tilly",
    "10": "Gran Mendoza",
    "12": "Corrientes",
    "13": "Gran Córdoba",
    "14": "Concordia",
    "15": "Formosa",
    "17": "Neuquén-Plottier",
    "18": "Santiago del Estero-La Banda",
    "19": "Jujuy-Palpalá",
    "20": "Río Gallegos",
    "22": "Gran Catamarca",
    "23": "Gran Salta",
    "25": "La Rioja",
    "26": "Gran San Luis",
    "27": "Gran San Juan",
    "29": "Gran Tucumán-Tafí Viejo",
    "30": "Santa Rosa-Toay",
    "31": "Ushuaia-Río Grande",
    "32": "Ciudad Autónoma de Buenos Aires",
    "33": "Partidos del Gran Buenos Aires",
    "34": "Mar del Plata",
    "36": "Río Cuarto",
    "38": "San Nicolás-Villa Constitución",
    "91": "Rawson-Trelew",
    "93": "Viedma-Carmen de Patagones",
}
