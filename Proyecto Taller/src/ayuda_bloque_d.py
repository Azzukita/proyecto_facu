"""Ejemplos de pandas del Bloque D para la hoja de ayuda (P6).

Trabajan con los datos del mapa: los aglomerados con sus coordenadas
(aglomerados_coordenadas.json) y los resultados del Bloque B. El módulo
del mapa (mapa_indicadores.py) solo usa un merge: los demás ejemplos
aplican agg, unstack y pivot_table a esa misma tabla, por región.
"""
from src import mapa_indicadores as mi
from src import mercado_laboral as ml
from src import regiones, rutas
from src.ayuda_comun import (
    Ejemplo, TEMA_AGREGACIONES, TEMA_GRAFICO, TEMA_MERGE, tablas_iguales)

RESUMEN = (
    "**Lo que usa el módulo `mapa_indicadores.py`:** un `merge` con "
    "`how='left'` (`unir_con_aglomerados`) entre los aglomerados del mapa "
    "y los resultados, con los códigos normalizados a dos dígitos. No "
    "agrupa ni reestructura: recibe las tablas de los Bloques B y C ya "
    "calculadas. Los ejemplos 1, 2, 5 y 6 aplican `groupby`, `agg`, "
    "`unstack` y `pivot_table` a la tabla del mapa, agrupando por región."
)

RUTA_COORDENADAS = (
    rutas.RAIZ_PROYECTO / "maps" / "aglomerados_coordenadas.json")


def ejemplo_sum(mapa):
    """Suma simple: ocupados ponderados por región."""
    return mapa.groupby("region")["ocupados"].sum().round().to_frame(
        "ocupados_ponderados")


def ejemplo_agg(mapa):
    """Varias agregaciones a la vez con agg() y tasa ponderada."""
    por_region = mapa.groupby("region").agg(
        aglomerados=("codigo", "count"),
        tasa_minima=("valor", "min"),
        tasa_maxima=("valor", "max"),
        desocupados=("desocupados", "sum"),
        pea=("pea", "sum"),
    )
    por_region["tasa_region"] = 100 * por_region["desocupados"] / (
        por_region["pea"])
    return por_region.drop(columns=["desocupados", "pea"]).round(2)


def ejemplo_merge_normalizado(aglomerados, tabla_periodo):
    """Merge left con los códigos normalizados: cuántos tienen dato."""
    unido = mi.unir_con_aglomerados(
        aglomerados, tabla_periodo, "AGLOMERADO", "tasa_desempleo")
    con_dato = unido["valor"].notna().map(
        {True: "con dato", False: "sin dato"})
    return con_dato.value_counts().rename_axis("aglomerados").to_frame(
        "cantidad")


def ejemplo_merge_sin_normalizar(aglomerados, tabla_periodo):
    """El mismo merge sin normalizar: los códigos '02' y '2' no coinciden."""
    cruce = aglomerados.merge(
        tabla_periodo, left_on="codigo", right_on="AGLOMERADO",
        how="left", indicator=True)
    return cruce["_merge"].value_counts().rename_axis(
        "resultado del merge").to_frame("aglomerados")


def ejemplo_groupby_unstack(trimestral):
    """Tasa de desempleo por región y trimestre: groupby + unstack."""
    sumas = trimestral.groupby(["region", "periodo"])[
        ["desocupados", "pea"]].sum()
    tasa = 100 * sumas["desocupados"] / sumas["pea"]
    return tasa.unstack().round(2)


def ejemplo_pivot_table(trimestral):
    """El mismo resultado con pivot_table."""
    sumas = trimestral.pivot_table(
        index="region", columns="periodo",
        values=["desocupados", "pea"], aggfunc="sum")
    return (100 * sumas["desocupados"] / sumas["pea"]).round(2)


EJEMPLOS = (
    Ejemplo(
        TEMA_AGREGACIONES,
        "1. Suma simple con groupby().sum()",
        "Una sola agregación sobre la tabla del mapa: cuántos ocupados "
        "(ponderados) hay en cada región, sumando sus aglomerados.",
        ejemplo_sum, ("mapa",)),
    Ejemplo(
        TEMA_AGREGACIONES,
        "2. Varias agregaciones con groupby().agg()",
        "Con agg() se obtienen en una pasada la cantidad de aglomerados, "
        "la tasa mínima y máxima (lo que usa la leyenda del mapa, "
        "`resumen_rango`) y las sumas con las que se calcula la tasa de "
        "la región. La tasa se calcula con las sumas y no como promedio "
        "de las tasas de los aglomerados, para que quede ponderada.",
        ejemplo_agg, ("mapa",)),
    Ejemplo(
        TEMA_MERGE,
        "3. merge de los aglomerados con los resultados (el del mapa)",
        "Es el merge de `unir_con_aglomerados`: how='left' deja todos los "
        "aglomerados en el mapa, aunque no tengan dato, y antes se "
        "normalizan los códigos a dos dígitos ('2' pasa a '02'). Acá se "
        "cuenta cuántos tienen dato.",
        ejemplo_merge_normalizado, ("aglomerados", "tabla_periodo")),
    Ejemplo(
        TEMA_MERGE,
        "4. El mismo merge sin normalizar los códigos",
        "Muestra por qué se normaliza: el JSON de coordenadas trae '02' y "
        "los resultados '2'. Sin normalizar, esos aglomerados no tienen "
        "pareja (`left_only`) y quedarían sin color en el mapa. "
        "indicator=True permite verlo.",
        ejemplo_merge_sin_normalizar, ("aglomerados", "tabla_periodo")),
    Ejemplo(
        TEMA_GRAFICO,
        "5. Estructura de la tabla con groupby() + unstack()",
        "groupby suma los desocupados y la PEA por región y trimestre, se "
        "calcula la tasa y unstack pasa los trimestres a columnas: una "
        "fila por región, lista para comparar en un gráfico.",
        ejemplo_groupby_unstack, ("trimestral",)),
    Ejemplo(
        TEMA_GRAFICO,
        "6. Lo mismo con pivot_table()",
        "Da la misma tabla en una sola llamada. El mapa no la necesita: "
        "pinta un período por vez, con una fila por aglomerado.",
        ejemplo_pivot_table, ("trimestral",)),
)


def preparar_datos(individuos, ruta_json=None):
    """Prepara los datos que usan los ejemplos del Bloque D.

    Args:
        individuos: DataFrame de ml.cargar_datos_individuos.
        ruta_json: ruta del JSON de aglomerados (por defecto el de la
            carpeta maps del proyecto).

    Returns:
        Diccionario con 'aglomerados' (con región y provincia),
        'tabla_periodo' (resultados anuales del último período),
        'mapa' (aglomerados unidos con ese período, como lo pinta el mapa)
        y 'trimestral' (resultados por trimestre, con la región).

    Raises:
        FileNotFoundError: si no hay archivos de individuos.
    """
    if individuos.empty:
        raise FileNotFoundError(
            "No se encontraron archivos de individuos de Mercado Laboral.")
    aglomerados = regiones.cargar_aglomerados(ruta_json or RUTA_COORDENADAS)
    anual = ml.preparar_datos_mapa(individuos, "anual")
    ultimo = mi.periodos_disponibles(anual)[-1]
    tabla_periodo = mi.tabla_del_periodo(anual, ultimo)
    mapa = mi.unir_con_aglomerados(
        aglomerados, tabla_periodo, "AGLOMERADO", "tasa_desempleo")
    trimestral = ml.preparar_datos_mapa(individuos, "trimestral")
    trimestral = trimestral.assign(
        codigo=trimestral["AGLOMERADO"].map(regiones.normalizar_codigo)
    ).merge(aglomerados[["codigo", "region"]], on="codigo", how="left")
    return {"aglomerados": aglomerados, "tabla_periodo": tabla_periodo,
            "mapa": mapa, "trimestral": trimestral}


def son_equivalentes(datos):
    """Comprueba que groupby + unstack y pivot_table dan lo mismo.

    Args:
        datos: resultado de preparar_datos.

    Returns:
        True si las dos tablas coinciden.
    """
    trimestral = datos["trimestral"]
    return tablas_iguales(ejemplo_groupby_unstack(trimestral),
                          ejemplo_pivot_table(trimestral))