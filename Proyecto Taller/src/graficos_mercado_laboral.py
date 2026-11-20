"""Gráficos del Bloque B (Mercado Laboral y Género), hechos con Altair.

Cada función recibe las tablas que arma src.mercado_laboral y devuelve un
gráfico. La página de Streamlit solo los muestra.
"""
import altair as alt
import pandas as pd

from src import config, mercado_laboral as ml

# Un color fijo por sexo para que sea el mismo en todos los gráficos.
COLORES_SEXO = {
    ml.TOTAL_SEXO: "#6c757d",
    config.NOMBRES_SEXO[config.SEXO_VARON]: "#1f77b4",
    config.NOMBRES_SEXO[config.SEXO_MUJER]: "#d6336c",
}
COLORES_ESTADO = {
    "Ocupados": "#2a9d8f",
    "Desocupados": "#e76f51",
    "Inactivos": "#adb5bd",
}
ETIQUETA_METRICA = {v: k for k, v in ml.METRICAS_EVOLUCION.items()}


def _orden_periodos(tabla):
    """Devuelve las etiquetas de período en orden cronológico."""
    columnas = [c for c in ("ANO4", "TRIMESTRE") if c in tabla.columns]
    ordenada = tabla.sort_values(columnas)
    return ordenada["periodo"].drop_duplicates().tolist()


def _filtrar_sexos(tabla, sexos):
    """Deja solo los sexos pedidos (None = todos los de la tabla)."""
    if sexos is None:
        return tabla
    return tabla[tabla["sexo"].isin(list(sexos))]


def _escala_sexo():
    """Escala de color con un color fijo por sexo."""
    return alt.Scale(domain=list(COLORES_SEXO),
                     range=list(COLORES_SEXO.values()))


def grafico_evolucion(tabla, metrica="tasa_desempleo", sexos=None,
                      columnas=2):
    """Líneas de la evolución: un panel por aglomerado y una línea por sexo.

    Es el gráfico principal: el tiempo va en el eje X, el indicador en el
    eje Y, el sexo en el color y la geografía en los paneles.

    Args:
        tabla: resultado de ml.preparar_datos_evolucion.
        metrica: columna a graficar (ver ml.METRICAS_EVOLUCION).
        sexos: sexos a mostrar (None = todos).
        columnas: cantidad de paneles por fila.

    Returns:
        Gráfico de Altair.
    """
    datos = _filtrar_sexos(tabla, sexos)
    etiqueta = ETIQUETA_METRICA.get(metrica, metrica)
    return (
        alt.Chart(datos)
        .mark_line(point=True)
        .encode(
            x=alt.X("periodo:N", sort=_orden_periodos(tabla),
                    title="Período", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y(f"{metrica}:Q", title=etiqueta),
            color=alt.Color("sexo:N", scale=_escala_sexo(), title="Sexo"),
            tooltip=[
                alt.Tooltip("aglomerado_nombre:N", title="Aglomerado"),
                alt.Tooltip("periodo:N", title="Período"),
                alt.Tooltip("sexo:N", title="Sexo"),
                alt.Tooltip(f"{metrica}:Q", title=etiqueta, format=".2f"),
            ],
        )
        .properties(width=260, height=170)
        .facet(facet=alt.Facet("aglomerado_nombre:N", title=None),
               columns=columnas)
    )


def grafico_barras_agrupadas(tabla, metrica="tasa_desempleo", sexos=None):
    """Barras agrupadas por sexo para el último período de la tabla.

    Args:
        tabla: resultado de ml.preparar_datos_evolucion.
        metrica: columna a graficar (ver ml.METRICAS_EVOLUCION).
        sexos: sexos a mostrar (None = todos).

    Returns:
        Gráfico de Altair.
    """
    ultimo = _orden_periodos(tabla)[-1]
    datos = _filtrar_sexos(tabla[tabla["periodo"] == ultimo], sexos)
    etiqueta = ETIQUETA_METRICA.get(metrica, metrica)
    return (
        alt.Chart(datos)
        .mark_bar()
        .encode(
            x=alt.X("aglomerado_nombre:N", title=None,
                    sort=alt.EncodingSortField(field=metrica, op="max",
                                               order="descending"),
                    axis=alt.Axis(labelAngle=-45)),
            xOffset=alt.XOffset("sexo:N"),
            y=alt.Y(f"{metrica}:Q", title=etiqueta),
            color=alt.Color("sexo:N", scale=_escala_sexo(), title="Sexo"),
            tooltip=[
                alt.Tooltip("aglomerado_nombre:N", title="Aglomerado"),
                alt.Tooltip("sexo:N", title="Sexo"),
                alt.Tooltip(f"{metrica}:Q", title=etiqueta, format=".2f"),
            ],
        )
        .properties(width=420, height=260,
                    title=f"Último período: {ultimo}")
    )


def grafico_mapa_calor(tabla, metrica="tasa_desempleo", sexos=None):
    """Mapa de calor aglomerado x período, con un panel por sexo.

    Args:
        tabla: resultado de ml.preparar_datos_evolucion.
        metrica: columna que da el color (ver ml.METRICAS_EVOLUCION).
        sexos: sexos a mostrar (None = todos).

    Returns:
        Gráfico de Altair.
    """
    datos = _filtrar_sexos(tabla, sexos)
    etiqueta = ETIQUETA_METRICA.get(metrica, metrica)
    orden_sexos = [s for s in COLORES_SEXO if s in set(datos["sexo"])]
    return (
        alt.Chart(datos)
        .mark_rect()
        .encode(
            x=alt.X("periodo:N", sort=_orden_periodos(tabla),
                    title="Período", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("aglomerado_nombre:N", title=None),
            color=alt.Color(f"{metrica}:Q", title=etiqueta,
                            scale=alt.Scale(scheme="orangered")),
            tooltip=[
                alt.Tooltip("aglomerado_nombre:N", title="Aglomerado"),
                alt.Tooltip("periodo:N", title="Período"),
                alt.Tooltip("sexo:N", title="Sexo"),
                alt.Tooltip(f"{metrica}:Q", title=etiqueta, format=".2f"),
            ],
        )
        .properties(width=200, height=alt.Step(22))
        .facet(column=alt.Column("sexo:N", sort=orden_sexos, title=None))
    )


def grafico_distribucion(largo, columnas=2):
    """Barras apiladas con la distribución ocupados/desocupados/inactivos.

    Args:
        largo: resultado de ml.preparar_datos_distribucion.
        columnas: cantidad de paneles por fila.

    Returns:
        Gráfico de Altair, con un panel por aglomerado.
    """
    orden = list(COLORES_ESTADO)
    return (
        alt.Chart(largo)
        .mark_bar()
        .encode(
            x=alt.X("periodo:N", sort=_orden_periodos(largo),
                    title="Período", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("porcentaje:Q", title="% de la población",
                    scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("estado:N", title="Condición",
                            scale=alt.Scale(domain=orden,
                                            range=list(
                                                COLORES_ESTADO.values()))),
            order=alt.Order("estado:N", sort="ascending"),
            tooltip=[
                alt.Tooltip("aglomerado_nombre:N", title="Aglomerado"),
                alt.Tooltip("periodo:N", title="Período"),
                alt.Tooltip("estado:N", title="Condición"),
                alt.Tooltip("porcentaje:Q", title="%", format=".2f"),
            ],
        )
        .properties(width=260, height=170)
        .facet(facet=alt.Facet("aglomerado_nombre:N", title=None),
               columns=columnas)
    )


def grafico_brechas(brechas, metrica="tasa_desempleo"):
    """Líneas de la brecha de género (mujer - varón) por aglomerado.

    Args:
        brechas: resultado de ml.preparar_datos_brechas.
        metrica: indicador sobre el que se calculó la brecha.

    Returns:
        Gráfico de Altair con una línea de referencia en 0.
    """
    columna = "brecha_" + metrica
    etiqueta = ETIQUETA_METRICA.get(metrica, metrica)
    lineas = (
        alt.Chart(brechas)
        .mark_line(point=True)
        .encode(
            x=alt.X("periodo:N", sort=_orden_periodos(brechas),
                    title="Período", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y(f"{columna}:Q",
                    title="Brecha (mujer - varón), puntos porcentuales"),
            color=alt.Color("aglomerado_nombre:N", title="Aglomerado"),
            tooltip=[
                alt.Tooltip("aglomerado_nombre:N", title="Aglomerado"),
                alt.Tooltip("periodo:N", title="Período"),
                alt.Tooltip(f"{columna}:Q", title=f"Brecha ({etiqueta})",
                            format=".2f"),
            ],
        )
    )
    cero = (alt.Chart(pd.DataFrame({"y": [0]}))
            .mark_rule(color="black", strokeDash=[4, 4]).encode(y="y:Q"))
    return (lineas + cero).properties(width=560, height=300)