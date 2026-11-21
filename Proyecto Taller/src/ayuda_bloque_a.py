"""Ejemplos de pandas del Bloque A para la hoja de ayuda (P6).

Trabajan con los informes de calidad que generan los notebooks de la
primera etapa (carpeta de salida). El panel de calidad (panel_calidad.py)
no usa agg(), merge ni pivot_table: estos ejemplos muestran cómo se
resolverían esos mismos datos con cada estrategia.
"""
import pandas as pd

from src import config, panel_calidad
from src.ayuda_comun import (
    Ejemplo, TEMA_AGREGACIONES, TEMA_GRAFICO, TEMA_MERGE, tablas_iguales)

RESUMEN = (
    "**Lo que usa el panel:** una agregación simple, "
    "`groupby().mean()`, para el promedio de faltantes por etiqueta; "
    "conteos con un bucle sobre diccionarios, y DataFrames armados con "
    "`pd.DataFrame` a partir de listas de diccionarios (ya salen en "
    "formato ancho, por eso no hace falta reestructurarlos). "
    "**No usa** `agg()`, `merge` ni `pivot_table`/`unstack`: los ejemplos "
    "de abajo los muestran sobre los mismos informes."
)

ETIQUETAS_FALTANTES = ("Supera umbral", "No supera umbral")


def _elegir_informe(informes):
    """Elige el informe 'calidad_datos.json' o, si no está, el primero."""
    if "calidad_datos.json" in informes:
        return informes["calidad_datos.json"]
    return list(informes.values())[0]


def tabla_faltantes(informe):
    """Arma una tabla con los faltantes de todos los trimestres.

    Usa armar_tabla_faltantes del panel para cada trimestre y las junta.

    Args:
        informe: informe con el bloque de completitud.

    Returns:
        DataFrame con la columna 'Trimestre' y las de armar_tabla_faltantes.
    """
    completitud = panel_calidad.extraer_datos_completitud(informe)
    tablas = []
    for trimestre, datos in completitud["por_trimestre"].items():
        tabla = panel_calidad.armar_tabla_faltantes(
            datos["columnas"], [], ETIQUETAS_FALTANTES)
        if tabla.empty:
            continue
        tabla.insert(0, "Trimestre", trimestre)
        tablas.append(tabla)
    return pd.concat(tablas, ignore_index=True)


def tabla_inconsistencias(informe):
    """Arma una tabla con una fila por regla y trimestre.

    Args:
        informe: informe con el bloque de inconsistencias.

    Returns:
        DataFrame con Trimestre, Regla, Etiqueta, Registros afectados y
        Columnas.
    """
    consistencia = panel_calidad.extraer_datos_consistencia(informe)
    filas = []
    for trimestre, datos in consistencia["por_trimestre"].items():
        for regla, detalle in datos["reglas"].items():
            filas.append({
                "Trimestre": trimestre,
                "Regla": regla,
                "Etiqueta": detalle["etiqueta"],
                "Registros afectados": detalle["cantidad"],
                "Columnas": ", ".join(detalle["columnas"]),
            })
    return pd.DataFrame(filas)


def tabla_roles():
    """Arma una tabla con una fila por rol y columna (config.ROLES)."""
    filas = [(rol, columna) for rol, columnas in config.ROLES.items()
             for columna in columnas]
    return pd.DataFrame(filas, columns=["Rol", "Columna"])


def ejemplo_sum(inconsistencias):
    """Suma simple: registros afectados por etiqueta."""
    return (inconsistencias.groupby("Etiqueta")["Registros afectados"]
            .sum().sort_values(ascending=False).to_frame())


def ejemplo_agg(faltantes):
    """Varias agregaciones a la vez con agg() y nombres de salida."""
    sobre_umbral = faltantes["Etiqueta"].eq("Supera umbral")
    return faltantes.assign(sobre_umbral=sobre_umbral).groupby(
        "Trimestre").agg(
        columnas=("Columna", "count"),
        faltante_promedio=("Porcentaje Faltantes (%)", "mean"),
        faltante_maximo=("Porcentaje Faltantes (%)", "max"),
        columnas_sobre_umbral=("sobre_umbral", "sum"),
    ).round(2)


def ejemplo_merge_roles(roles, faltantes):
    """Merge left de los roles con los faltantes del último trimestre."""
    ultimo = faltantes[faltantes["Trimestre"] == faltantes["Trimestre"].max()]
    return roles.merge(
        ultimo[["Columna", "Porcentaje Faltantes (%)"]],
        on="Columna", how="left", indicator=True)


def ejemplo_groupby_unstack(faltantes):
    """% de faltantes por columna y trimestre: groupby + unstack."""
    tabla = faltantes.groupby(["Columna", "Trimestre"])[
        "Porcentaje Faltantes (%)"].mean().unstack(fill_value=0)
    return tabla.sort_values(
        tabla.columns[-1], ascending=False).head(8).round(2)


def ejemplo_pivot_table(faltantes):
    """El mismo resultado con pivot_table."""
    tabla = faltantes.pivot_table(
        index="Columna", columns="Trimestre",
        values="Porcentaje Faltantes (%)", aggfunc="mean", fill_value=0)
    return tabla.sort_values(
        tabla.columns[-1], ascending=False).head(8).round(2)


EJEMPLOS = (
    Ejemplo(
        TEMA_AGREGACIONES,
        "1. Suma simple con groupby().sum()",
        "Una sola agregación: cuántos registros afectados hay por "
        "etiqueta (suma de todos los trimestres). Es lo que el panel hace "
        "con un bucle en `contar_por_etiqueta`; con pandas alcanza una "
        "línea.",
        ejemplo_sum, ("inconsistencias",)),
    Ejemplo(
        TEMA_AGREGACIONES,
        "2. Varias agregaciones con groupby().agg()",
        "Con agg() se calculan en una pasada la cantidad de columnas, el "
        "faltante promedio, el máximo y cuántas superan el umbral, cada "
        "uno con su nombre de columna.",
        ejemplo_agg, ("faltantes",)),
    Ejemplo(
        TEMA_MERGE,
        "3. merge entre los roles y los faltantes",
        "Une la tabla de roles (config.ROLES) con los faltantes del "
        "último trimestre por columna. how='left' conserva todas las "
        "columnas del rol e indicator=True marca cuáles no están en el "
        "informe (`left_only`): es lo que el panel hace con "
        "`columnas_sin_datos`.",
        ejemplo_merge_roles, ("roles", "faltantes")),
    Ejemplo(
        TEMA_GRAFICO,
        "4. Estructura del gráfico con groupby() + unstack()",
        "groupby agrupa por columna y trimestre; unstack pasa los "
        "trimestres a columnas. Queda una fila por columna analizada, "
        "lista para un gráfico de barras o líneas. fill_value=0 evita "
        "huecos si una columna no está en algún trimestre.",
        ejemplo_groupby_unstack, ("faltantes",)),
    Ejemplo(
        TEMA_GRAFICO,
        "5. Lo mismo con pivot_table()",
        "Da la misma tabla en una sola llamada. El panel no necesita "
        "ninguna de las dos porque arma la tabla ancha directamente al "
        "leer el JSON (`armar_tabla_faltantes`).",
        ejemplo_pivot_table, ("faltantes",)),
)


def preparar_datos():
    """Carga y prepara los datos que usan los ejemplos del Bloque A.

    Returns:
        Diccionario con 'faltantes', 'inconsistencias' y 'roles'.

    Raises:
        FileNotFoundError: si faltan los informes de calidad (hay que
            ejecutar los notebooks de Mercado Laboral).
    """
    informes = panel_calidad.cargar_todos_los_informes()
    con_faltantes = panel_calidad.informes_de_faltantes(informes)
    con_consistencia = panel_calidad.informes_de_consistencia(informes)
    if not con_faltantes or not con_consistencia:
        raise FileNotFoundError(
            "No hay informes de calidad en "
            f"{config.DIR_SALIDA}. Ejecutá los notebooks de Mercado "
            "Laboral para generarlos.")
    return {
        "faltantes": tabla_faltantes(_elegir_informe(con_faltantes)),
        "inconsistencias": tabla_inconsistencias(
            _elegir_informe(con_consistencia)),
        "roles": tabla_roles(),
    }


def son_equivalentes(datos):
    """Comprueba que groupby + unstack y pivot_table dan lo mismo.

    Args:
        datos: resultado de preparar_datos.

    Returns:
        True si las dos tablas coinciden.
    """
    faltantes = datos["faltantes"]
    return tablas_iguales(ejemplo_groupby_unstack(faltantes),
                          ejemplo_pivot_table(faltantes))
