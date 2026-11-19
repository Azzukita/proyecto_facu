"""Bloque C (segunda etapa): tecnología y condiciones de habitabilidad.

Todo el cálculo de la página "Hogares y Tecnología" vive acá, con pandas. La
página de Streamlit solo llama a estas funciones y dibuja el resultado.

Tiene dos partes:

1. Lectura de los informes de penetración tecnológica de la primera etapa
   (JSON en ``output/``).
2. Cruce de los hogares del módulo TIC con los hogares de Mercado Laboral
   para relacionar la calidad tecnológica con la vivienda.
"""
import json

import pandas as pd

from src import config, data_loader

# Nombres de las columnas calculadas (se usan en tablas, gráficos y CSV).
COL_REGION = "REGION_COD"
COL_CALIDAD = "CALIDAD_TEC"
COL_PESO = "PESO"
COL_TIENE_PC = "TIENE_PC"
COL_TIENE_INTERNET = "TIENE_INTERNET"
COLS_CLAVE = list(config.COLS_ID_HOGAR)

# Columnas de la tabla de resultados (lo que se muestra y se descarga).
COL_GRUPO = "Grupo de vivienda"
COL_CATEGORIA = "Calidad tecnológica"
COL_MUESTRA = "Hogares (muestra)"
COL_EXPANDIDOS = "Hogares (ponderados)"
COL_PORCENTAJE = "Porcentaje (%)"


# =============================================================================
# PARTE 1: INFORMES DE PENETRACIÓN TECNOLÓGICA (JSON de la primera etapa)
# =============================================================================
def buscar_informe_tecnologia(directorio=None):
    """Busca el informe de tecnología más reciente.

    La primera etapa puede guardar varios archivos (con fecha y hora en el
    nombre si el informe ya existía), así que se toma el último por nombre.

    Args:
        directorio: carpeta de informes (por defecto config.DIR_SALIDA).

    Returns:
        Ruta (Path) del informe, o None si no hay ninguno.
    """
    directorio = directorio or config.DIR_SALIDA
    candidatos = sorted(directorio.glob(config.PATRON_INFORME_TECNOLOGIA))
    return candidatos[-1] if candidatos else None


def cargar_informe_tecnologia(ruta=None):
    """Lee el informe de penetración tecnológica de la primera etapa.

    Args:
        ruta: archivo a leer (por defecto, el más reciente de la carpeta
            de informes).

    Returns:
        El informe como diccionario, o None si no existe o está dañado.
    """
    ruta = ruta or buscar_informe_tecnologia()
    if ruta is None:
        return None
    try:
        with open(ruta, encoding=config.ENCODING) as archivo:
            return json.load(archivo)
    except (OSError, json.JSONDecodeError):
        return None


def anios_del_informe(informe):
    """Lista los años disponibles en el informe, ordenados.

    Args:
        informe: diccionario devuelto por cargar_informe_tecnologia.

    Returns:
        Lista de años como texto (vacía si el informe no tiene años).
    """
    return sorted((informe or {}).get("anios", {}))


def _clave_nivel(nivel):
    """Devuelve la clave del informe para 'region' o 'aglomerado'."""
    if nivel not in ("region", "aglomerado"):
        raise ValueError("nivel debe ser 'region' o 'aglomerado'")
    return "por_" + nivel


def tabla_penetracion(informe, anio, nivel):
    """Arma la tabla de penetración tecnológica de un año.

    Args:
        informe: diccionario del informe de tecnología.
        anio: año como texto, por ejemplo '2024'.
        nivel: 'region' o 'aglomerado'.

    Returns:
        DataFrame con una fila por región o aglomerado: Código, Nombre,
        hogares (muestra y ponderados) y el % de hogares con computadora,
        internet y celular. Vacío si el año no está en el informe.
    """
    bloques = informe.get("anios", {}).get(anio, {}).get(_clave_nivel(nivel))
    if not bloques:
        return pd.DataFrame()
    tabla = pd.DataFrame.from_dict(bloques, orient="index")
    tabla.index.name = "Código"
    tabla = tabla.reset_index()
    tabla = tabla.rename(columns={
        "nombre": "Nombre",
        "hogares_muestra": "Hogares (muestra)",
        "hogares_ponderados": "Hogares (ponderados)",
        "pct_computadora": "Computadora (%)",
        "pct_internet": "Internet (%)",
        "pct_celular": "Celular (%)",
    })
    columnas = ["Código", "Nombre", "Hogares (muestra)",
                "Hogares (ponderados)", "Computadora (%)", "Internet (%)",
                "Celular (%)"]
    return tabla[columnas]


def opciones_por_defecto(tabla, nivel):
    """Elige qué grupos geográficos se preseleccionan.

    Regiones: todas (son pocas). Aglomerados: los de más hogares
    ponderados (config.N_AGLOMERADOS_DEFECTO), para que el gráfico no
    arranque con 32 barras.

    Args:
        tabla: resultado de tabla_penetracion.
        nivel: 'region' o 'aglomerado'.

    Returns:
        Lista de nombres a preseleccionar.
    """
    if tabla.empty:
        return []
    if nivel == "region":
        return tabla["Nombre"].tolist()
    mayores = tabla.nlargest(config.N_AGLOMERADOS_DEFECTO,
                             "Hogares (ponderados)")
    return mayores["Nombre"].tolist()


def filtrar_penetracion(tabla, nombres):
    """Deja solo los grupos geográficos elegidos.

    Args:
        tabla: resultado de tabla_penetracion.
        nombres: lista de nombres de región o aglomerado.

    Returns:
        DataFrame filtrado (mismas columnas), con índice reiniciado.
    """
    return tabla[tabla["Nombre"].isin(nombres)].reset_index(drop=True)