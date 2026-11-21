"""Une los resultados de los bloques B y C con los aglomerados del mapa.

No recalcula indicadores: recibe las tablas que producen
``mercado_laboral.preparar_datos_mapa`` (bloque B) y
``hogares_tecnologia.acceso_por_aglomerado`` (bloque C), las une con el
DataFrame de aglomerados por código y arma colores y textos para el mapa.
"""
import pandas as pd

from src import config, regiones

COLOR_SIN_DATO = [190, 190, 190, 255]
COLOR_BAJO = (255, 245, 157)
COLOR_ALTO = (183, 28, 28)

# Bloque B: indicador a pintar -> columna de preparar_datos_mapa.
INDICADORES_LABORALES = {
    "Tasa de desempleo (%)": "tasa_desempleo",
    "Ocupados (% de la población)": "pct_ocupados",
    "Inactivos (% de la población)": "pct_inactivos",
    "Brecha de género en desempleo (mujeres − varones, p.p.)":
        "brecha_tasa_desempleo",
}
# Bloque B: datos que se muestran al pasar el cursor.
DETALLE_LABORAL = {
    "Tasa de desempleo (%)": "tasa_desempleo",
    "Desempleo varones (%)": "tasa_desempleo_varon",
    "Desempleo mujeres (%)": "tasa_desempleo_mujer",
    "Ocupados (%)": "pct_ocupados",
    "Desocupados (%)": "pct_desocupados",
    "Inactivos (%)": "pct_inactivos",
}


def periodos_disponibles(tabla):
    """Lista los períodos de la tabla del bloque B, en orden.

    Args:
        tabla: resultado de ``preparar_datos_mapa``.

    Returns:
        Lista de etiquetas de período (por ejemplo '2024-T1' o '2024').
    """
    return sorted(tabla["periodo"].unique())


def tabla_del_periodo(tabla, periodo):
    """Deja solo las filas de un período.

    Args:
        tabla: resultado de ``preparar_datos_mapa``.
        periodo: etiqueta de período.

    Returns:
        DataFrame filtrado, con índice reiniciado.
    """
    return tabla[tabla["periodo"] == periodo].reset_index(drop=True)


def unir_con_aglomerados(aglomerados, tabla, col_codigo, col_valor):
    """Une una tabla de resultados con los aglomerados del mapa.

    Los códigos se normalizan a dos dígitos antes de unir (los resultados
    traen '2' y el JSON de coordenadas '02'). Es un merge 'left': todos los
    aglomerados quedan en el mapa, aunque no tengan dato.

    Args:
        aglomerados: DataFrame de ``regiones.cargar_aglomerados``.
        tabla: resultados por aglomerado.
        col_codigo: columna de ``tabla`` con el código de aglomerado.
        col_valor: columna de ``tabla`` que se pinta en el mapa.

    Returns:
        Copia de ``aglomerados`` con la columna ``valor`` y las demás
        columnas de ``tabla``.
    """
    resultados = tabla.copy()
    resultados["codigo"] = resultados[col_codigo].map(
        regiones.normalizar_codigo)
    resultados["valor"] = resultados[col_valor]
    resultados = resultados.drop(columns=[col_codigo]).drop_duplicates(
        "codigo")
    return aglomerados.merge(resultados, on="codigo", how="left")


def colores_por_valor(valores):
    """Asigna un color a cada valor, de claro (bajo) a oscuro (alto).

    Los valores faltantes quedan en gris. Si todos los valores son iguales,
    todos reciben el color bajo.

    Args:
        valores: serie numérica.

    Returns:
        Lista de colores [r, g, b, a], uno por valor.
    """
    minimo, maximo = valores.min(), valores.max()
    colores = []
    for valor in valores:
        if pd.isna(valor):
            colores.append(COLOR_SIN_DATO)
            continue
        t = 0 if maximo == minimo else (valor - minimo) / (maximo - minimo)
        rgb = [round(b + (a - b) * t) for b, a in zip(COLOR_BAJO, COLOR_ALTO)]
        colores.append(rgb + [255])
    return colores


def _formatear(valor):
    """Formatea un número con un decimal ('s/d' si falta)."""
    return "s/d" if pd.isna(valor) else f"{valor:.1f}".replace(".", ",")


def armar_textos(datos, detalle):
    """Arma el texto (HTML) que se muestra al pasar el cursor.

    Args:
        datos: DataFrame con ``aglomerado``, ``provincia`` y las columnas
            de ``detalle``.
        detalle: diccionario {título: columna} de lo que se muestra.

    Returns:
        Lista de textos HTML, uno por fila.
    """
    textos = []
    for _, fila in datos.iterrows():
        lineas = [f"<b>{fila['aglomerado']}</b>", fila["provincia"]]
        lineas += [f"{titulo}: {_formatear(fila[col])}"
                   for titulo, col in detalle.items() if col in fila.index]
        textos.append("<br/>".join(lineas))
    return textos


def resumen_rango(datos):
    """Devuelve el mínimo y el máximo de la columna ``valor``.

    Args:
        datos: DataFrame con la columna ``valor``.

    Returns:
        Tupla (minimo, maximo); (None, None) si no hay valores.
    """
    if datos["valor"].notna().sum() == 0:
        return None, None
    return float(datos["valor"].min()), float(datos["valor"].max())


def datos_mapa_laboral(aglomerados, tabla, periodo, indicador):
    """Arma los datos del mapa del bloque B para un período e indicador.

    Args:
        aglomerados: DataFrame de ``regiones.cargar_aglomerados``.
        tabla: resultado de ``preparar_datos_mapa``.
        periodo: etiqueta de período ('2024-T1' o '2024').
        indicador: clave de ``INDICADORES_LABORALES``.

    Returns:
        DataFrame de aglomerados con ``valor``, ``color`` y ``texto``.
    """
    del_periodo = tabla_del_periodo(tabla, periodo)
    datos = unir_con_aglomerados(
        aglomerados, del_periodo, "AGLOMERADO",
        INDICADORES_LABORALES[indicador])
    datos["color"] = colores_por_valor(datos["valor"])
    datos["texto"] = armar_textos(datos, DETALLE_LABORAL)
    return datos


def datos_mapa_tecnologia(aglomerados, tabla, categoria):
    """Arma los datos del mapa del bloque C para una categoría.

    Args:
        aglomerados: DataFrame de ``regiones.cargar_aglomerados``.
        tabla: resultado de ``hogares_tecnologia.acceso_por_aglomerado``.
        categoria: categoría de calidad tecnológica a pintar (% de hogares).

    Returns:
        DataFrame de aglomerados con ``valor``, ``color`` y ``texto``.
    """
    datos = unir_con_aglomerados(aglomerados, tabla, "Código", categoria)
    datos["color"] = colores_por_valor(datos["valor"])
    detalle = {f"{c} (%)": c for c in config.CATEGORIAS_CALIDAD_TEC.values()}
    detalle["Hogares (muestra)"] = "Hogares (muestra)"
    datos["texto"] = armar_textos(datos, detalle)
    return datos
