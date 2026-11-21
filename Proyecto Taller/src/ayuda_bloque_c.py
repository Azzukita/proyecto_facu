"""Ejemplos de pandas del Bloque C para la hoja de ayuda (P6).

Cada ejemplo es una función corta que trabaja con los datos reales de hogares.
La hoja de ayuda muestra el código de la función (con inspect) y su resultado,
así que lo que se ve en pantalla es exactamente lo que se ejecuta.
"""
import pandas as pd

from src import config
from src import hogares_tecnologia as ht
from src.ayuda_comun import (
    Ejemplo, TEMA_AGREGACIONES, TEMA_GRAFICO, TEMA_MERGE, tablas_iguales)

RESUMEN = (
    "**Lo que usa el módulo `hogares_tecnologia.py`:** `groupby().agg()` "
    "con `unstack` para tener, por grupo de vivienda y calidad "
    "tecnológica, los hogares ponderados y la muestra; y un `merge` con "
    "`how='left'` y `validate='one_to_one'` para cruzar los hogares TIC "
    "con los de vivienda por la tupla (CODUSU, NRO_HOGAR, AGLOMERADO). "
    "`pivot_table` se compara en el ejemplo 6."
)


def ejemplo_sum(hogares):
    """Suma simple: hogares ponderados por región."""
    region = hogares[ht.COL_REGION].map(config.NOMBRES_REGIONES).rename(
        "Región")
    return hogares.groupby(region)[ht.COL_PESO].sum().round().to_frame(
        "hogares_ponderados")


def ejemplo_agg(hogares):
    """Varias agregaciones a la vez con agg() y nombres de salida."""
    region = hogares[ht.COL_REGION].map(config.NOMBRES_REGIONES).rename(
        "Región")
    return hogares.groupby(region).agg(
        hogares_muestra=(ht.COL_PESO, "size"),
        hogares_ponderados=(ht.COL_PESO, "sum"),
        peso_promedio=(ht.COL_PESO, "mean"),
    ).round(1)


def ejemplo_merge_hogares(hogares_tic, hogares_vivienda):
    """Merge left por la tupla del hogar, con validate e indicator."""
    hogares_tic = hogares_tic.drop_duplicates(ht.COLS_CLAVE)
    hogares_vivienda = hogares_vivienda.drop_duplicates(ht.COLS_CLAVE)
    cruce = hogares_tic.merge(
        hogares_vivienda, on=ht.COLS_CLAVE, how="left",
        validate="one_to_one", indicator=True)
    return cruce["_merge"].value_counts().rename_axis(
        "resultado del merge").to_frame("hogares")


def ejemplo_merge_regiones(hogares):
    """Merge con una tabla chica de nombres para agregar la región."""
    regiones = pd.DataFrame({
        ht.COL_REGION: list(config.NOMBRES_REGIONES),
        "Región": list(config.NOMBRES_REGIONES.values()),
    })
    con_nombre = hogares.merge(regiones, on=ht.COL_REGION, how="left")
    return (con_nombre[[config.COL_AGLOMERADO, ht.COL_REGION, "Región"]]
            .drop_duplicates().sort_values(ht.COL_REGION).head(8))


def ejemplo_groupby_unstack(hogares):
    """% de calidad tecnológica por tipo de vivienda: groupby + unstack."""
    vivienda = ht.etiquetar_vivienda(hogares["IV1"], "IV1").rename(
        "vivienda")
    pesos = hogares.groupby([vivienda, hogares[ht.COL_CALIDAD]])[
        ht.COL_PESO].sum().unstack(fill_value=0)
    return (pesos.div(pesos.sum(axis=1), axis=0) * 100).round(1)


def ejemplo_pivot_table(hogares):
    """El mismo resultado con pivot_table."""
    hogares = hogares.assign(
        vivienda=ht.etiquetar_vivienda(hogares["IV1"], "IV1"))
    pesos = hogares.pivot_table(
        index="vivienda", columns=ht.COL_CALIDAD, values=ht.COL_PESO,
        aggfunc="sum", fill_value=0)
    return (pesos.div(pesos.sum(axis=1), axis=0) * 100).round(1)


EJEMPLOS = (
    Ejemplo(
        TEMA_AGREGACIONES,
        "1. Suma simple con groupby().sum()",
        "Una sola agregación: cuántos hogares representa cada región "
        "(suma del peso POND_TIC). Es lo más corto, pero solo da un número "
        "por grupo.",
        ejemplo_sum, ("hogares",)),
    Ejemplo(
        TEMA_AGREGACIONES,
        "2. Varias agregaciones con groupby().agg()",
        "Con agg() se calculan en una pasada la muestra, los hogares "
        "ponderados y el peso promedio, cada uno con su nombre de columna. "
        "Se usó en el análisis para mostrar la muestra junto al porcentaje.",
        ejemplo_agg, ("hogares",)),
    Ejemplo(
        TEMA_MERGE,
        "3. merge entre los hogares TIC y los de Mercado Laboral",
        "Cruce por (CODUSU, NRO_HOGAR, AGLOMERADO). Antes se quitan las "
        "claves repetidas. how='left' conserva todos los hogares TIC, "
        "validate='one_to_one' avisa si todavía quedara alguna repetida e "
        "indicator=True permite contar cuáles tuvieron pareja.",
        ejemplo_merge_hogares, ("hogares_tic", "hogares_vivienda")),
    Ejemplo(
        TEMA_MERGE,
        "4. merge con una tabla de nombres",
        "Se agrega el nombre de la región uniendo con una tabla chica "
        "creada desde config.NOMBRES_REGIONES.",
        ejemplo_merge_regiones, ("hogares",)),
    Ejemplo(
        TEMA_GRAFICO,
        "5. Estructura del gráfico con groupby() + unstack()",
        "groupby agrupa por tipo de vivienda y calidad tecnológica; unstack "
        "pasa la calidad a columnas. Cada fila se divide por su total, así "
        "suma 100. Es la estrategia elegida para el gráfico.",
        ejemplo_groupby_unstack, ("hogares",)),
    Ejemplo(
        TEMA_GRAFICO,
        "6. Lo mismo con pivot_table()",
        "Da los mismos porcentajes en menos líneas. No se eligió porque "
        "con groupby + unstack es más fácil forzar las 4 categorías aunque "
        "alguna tenga 0 hogares y calcular otras columnas al mismo tiempo.",
        ejemplo_pivot_table, ("hogares",)),
)


def preparar_datos(anio):
    """Carga y prepara los datos que usan los ejemplos de un año.

    Args:
        anio: año como texto.

    Returns:
        Diccionario con 'hogares_tic' y 'hogares_vivienda' (sin cruzar) y
        'hogares' (cruzados, clasificados, con región y peso válido).

    Raises:
        FileNotFoundError: si faltan los archivos del año.
    """
    hogares_tic, hogares_vivienda = ht.cargar_hogares_del_anio(anio)
    base, _ = ht.armar_base_cruce(anio)
    validos, _ = ht._preparar_pesos(base, config.COLS_PESO_CRUCE[0])
    return {"hogares_tic": hogares_tic,
            "hogares_vivienda": hogares_vivienda,
            "hogares": validos}


def son_equivalentes(datos):
    """Comprueba que groupby + unstack y pivot_table dan lo mismo.

    Args:
        datos: resultado de preparar_datos.

    Returns:
        True si los porcentajes coinciden (tolerancia de redondeo).
    """
    hogares = datos["hogares"]
    return tablas_iguales(ejemplo_groupby_unstack(hogares),
                          ejemplo_pivot_table(hogares))