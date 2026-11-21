"""Ejemplos de pandas del Bloque B para la hoja de ayuda (P6).

Cada ejemplo es una función corta que trabaja con los datos reales de
individuos de Mercado Laboral. La hoja de ayuda muestra el código de la
función (con inspect) y su resultado, así que lo que se ve en pantalla es
exactamente lo que se ejecuta.
"""
import pandas as pd

from src import config
from src import mercado_laboral as ml
from src.ayuda_comun import (
    Ejemplo, TEMA_AGREGACIONES, TEMA_GRAFICO, TEMA_MERGE, tablas_iguales)

RESUMEN = (
    "**Lo que usa el módulo `mercado_laboral.py`:** `groupby().sum()` "
    "para sumar `PONDERA` y `unstack` para pasar los estados a columnas "
    "(`contar_poblacion_por_estado`); `merge` con `how='left'` para unir "
    "la tasa con la distribución (`_indicadores`) y el total con las "
    "brechas (`preparar_datos_mapa`); y `pivot_table` para pasar el sexo "
    "a columnas (`calcular_brechas_genero`). **No usa** `agg()`: el "
    "ejemplo 2 lo muestra sobre los mismos datos."
)

GRUPO = ["ANO4", "TRIMESTRE", config.COL_AGLOMERADO]


def ejemplo_sum(individuos):
    """Suma simple: población representada (suma de PONDERA)."""
    return individuos.groupby(["ANO4", "TRIMESTRE"])["PONDERA"].sum(
    ).to_frame("poblacion_ponderada")


def ejemplo_agg(individuos):
    """Varias agregaciones a la vez con agg() y nombres de salida."""
    return individuos.groupby(["ANO4", "TRIMESTRE"]).agg(
        personas_muestra=("PONDERA", "size"),
        poblacion_ponderada=("PONDERA", "sum"),
        peso_promedio=("PONDERA", "mean"),
    ).round(1)


def ejemplo_merge_indicadores(individuos):
    """Merge left de la distribución con la tasa, validando la unión."""
    tasa = ml.calcular_tasa_desempleo(individuos, GRUPO)
    distribucion = ml.calcular_distribucion_estado(individuos, GRUPO)
    cruce = distribucion.merge(
        tasa[GRUPO + ["pea", "tasa_desempleo"]],
        on=GRUPO, how="left", validate="one_to_one")
    return cruce[GRUPO + ["pct_ocupados", "pct_desocupados",
                          "pct_inactivos", "pea",
                          "tasa_desempleo"]].round(2).head(8)


def ejemplo_merge_nombres(individuos):
    """Merge con una tabla de nombres para agregar el aglomerado."""
    tasa = ml.calcular_tasa_desempleo(individuos, GRUPO)
    nombres = pd.DataFrame({
        config.COL_AGLOMERADO: list(config.AGLOMERADOS),
        "aglomerado": list(config.AGLOMERADOS.values()),
    })
    con_nombre = tasa.merge(nombres, on=config.COL_AGLOMERADO, how="left")
    return con_nombre[["ANO4", "TRIMESTRE", config.COL_AGLOMERADO,
                       "aglomerado", "tasa_desempleo"]].round(2).head(8)


def ejemplo_groupby_unstack(individuos):
    """% de ocupados, desocupados e inactivos: groupby + unstack."""
    base = individuos[individuos["ESTADO"].isin(config.ESTADOS_DISTRIBUCION)]
    pesos = base.groupby(["ANO4", "TRIMESTRE", "ESTADO"])[
        "PONDERA"].sum().unstack(fill_value=0)
    pesos = pesos.rename(columns=config.NOMBRES_ESTADO)
    return (pesos.div(pesos.sum(axis=1), axis=0) * 100).round(1)


def ejemplo_pivot_table(individuos):
    """El mismo resultado con pivot_table."""
    base = individuos[individuos["ESTADO"].isin(config.ESTADOS_DISTRIBUCION)]
    pesos = base.pivot_table(
        index=["ANO4", "TRIMESTRE"], columns="ESTADO", values="PONDERA",
        aggfunc="sum", fill_value=0).rename(columns=config.NOMBRES_ESTADO)
    return (pesos.div(pesos.sum(axis=1), axis=0) * 100).round(1)


EJEMPLOS = (
    Ejemplo(
        TEMA_AGREGACIONES,
        "1. Suma simple con groupby().sum()",
        "Una sola agregación: cuántas personas representa cada trimestre "
        "(suma del factor de expansión PONDERA). Así se calculan los "
        "ocupados, desocupados e inactivos del bloque.",
        ejemplo_sum, ("individuos",)),
    Ejemplo(
        TEMA_AGREGACIONES,
        "2. Varias agregaciones con groupby().agg()",
        "Con agg() se obtiene en una pasada la muestra (cuántas personas "
        "se encuestaron), la población que representan y el peso "
        "promedio. Muestra por qué hay que ponderar: la muestra son "
        "decenas de miles de personas y la población, millones.",
        ejemplo_agg, ("individuos",)),
    Ejemplo(
        TEMA_MERGE,
        "3. merge de la distribución con la tasa de desempleo",
        "Une dos tablas calculadas con las mismas claves (año, trimestre "
        "y aglomerado). how='left' conserva todas las filas de la "
        "distribución y validate='one_to_one' avisa si alguna clave "
        "estuviera repetida. Es lo que hace `_indicadores`.",
        ejemplo_merge_indicadores, ("individuos",)),
    Ejemplo(
        TEMA_MERGE,
        "4. merge con una tabla de nombres",
        "Agrega el nombre del aglomerado uniendo con una tabla chica "
        "creada desde config.AGLOMERADOS. El módulo hace lo mismo con "
        "`map()`, que es más corto cuando solo se agrega una columna. El "
        "cruce de individuos con hogares es del Bloque C.",
        ejemplo_merge_nombres, ("individuos",)),
    Ejemplo(
        TEMA_GRAFICO,
        "5. Estructura del gráfico con groupby() + unstack()",
        "groupby suma PONDERA por trimestre y estado; unstack pasa los "
        "estados a columnas y rename les pone nombre. Cada fila se divide "
        "por su total, así suma 100. Es la estrategia del módulo "
        "(`contar_poblacion_por_estado`).",
        ejemplo_groupby_unstack, ("individuos",)),
    Ejemplo(
        TEMA_GRAFICO,
        "6. Lo mismo con pivot_table()",
        "Da los mismos porcentajes en una sola llamada. En "
        "`calcular_brechas_genero` sí se usa pivot_table, porque ahí hay "
        "que pasar el sexo a columnas para varios indicadores a la vez.",
        ejemplo_pivot_table, ("individuos",)),
)


def preparar_datos(individuos):
    """Prepara los datos que usan los ejemplos del Bloque B.

    Args:
        individuos: DataFrame de ml.cargar_datos_individuos.

    Returns:
        Diccionario con 'individuos'.

    Raises:
        FileNotFoundError: si no hay archivos de individuos.
    """
    if individuos.empty:
        raise FileNotFoundError(
            "No se encontraron archivos de individuos de Mercado Laboral "
            f"en {config.DIR_DATOS}.")
    return {"individuos": individuos}


def son_equivalentes(datos):
    """Comprueba que groupby + unstack y pivot_table dan lo mismo.

    Args:
        datos: resultado de preparar_datos.

    Returns:
        True si las dos tablas coinciden.
    """
    individuos = datos["individuos"]
    return tablas_iguales(ejemplo_groupby_unstack(individuos),
                          ejemplo_pivot_table(individuos))
