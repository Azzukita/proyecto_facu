"""P5: mapas de Argentina con los resultados de los bloques B y C.

Vista general: seis áreas (una por región) y los aglomerados pintados según el
indicador elegido. Al hacer clic en una región se hace zoom y se ve el detalle
de sus aglomerados. Los cálculos viven en src/ (mapa_base, mapa_indicadores,
mercado_laboral y hogares_tecnologia); esta página solo arma la interfaz.
"""
from pathlib import Path
import sys

import pandas as pd
import pydeck as pdk
import streamlit as st

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent.parent
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from src import (config, data_loader, hogares_tecnologia as ht,  # noqa: E402
                 mapa_base, mapa_indicadores as mi, mercado_laboral as ml,
                 regiones)

TODO_EL_PAIS = "Todo el país"
MAPA_LABORAL = "Mercado laboral (Bloque B)"
MAPA_TECNOLOGIA = "Tecnología y hogares (Bloque C)"
TODOS_LOS_TIPOS = "Todos los tipos de vivienda"
RUTA_JSON = RAIZ_PROYECTO / "maps" / "aglomerados_coordenadas.json"
RUTA_GEOJSON = RAIZ_PROYECTO / "maps" / "provincias.geojson"


@st.cache_data
def obtener_datos(ruta_json):
    """Carga el DataFrame de aglomerados y lo cachea."""
    return regiones.cargar_aglomerados(ruta_json)


@st.cache_data
def obtener_areas(ruta_geojson):
    """Construye (una sola vez) las áreas de las regiones."""
    return mapa_base.construir_areas(ruta_geojson)


@st.cache_data(show_spinner="Leyendo mercado laboral...")
def tabla_laboral(periodicidad):
    """Prepara la tabla del bloque B ('trimestral' o 'anual')."""
    return ml.preparar_datos_mapa(ml.cargar_datos_individuos(), periodicidad)


@st.cache_data(show_spinner="Cruzando hogares...")
def base_tecnologia(anio):
    """Arma (una sola vez por año) la base de hogares del bloque C."""
    return ht.armar_base_cruce(anio)[0]


@st.cache_data
def anios_tecnologia():
    """Años en que se puede hacer el cruce del bloque C."""
    return ht.anios_disponibles_cruce(data_loader.escanear_datos())


def capa_areas(areas, region_activa):
    """Crea la capa de áreas de las regiones.

    Args:
        areas: DataFrame con ``region``, ``polygon`` y ``texto``.
        region_activa: región seleccionada o None (vista general). En la
            vista general las áreas son clickeables; con una región activa,
            esa se resalta y las demás se apagan.

    Returns:
        Capa PolygonLayer con id "areas".
    """
    datos = areas.copy()
    if region_activa is None:
        datos["color"] = datos["region"].map(
            lambda r: mapa_base.hex_a_rgba(mapa_base.COLORES_REGION[r], 110))
    else:
        datos["color"] = datos["region"].map(
            lambda r: mapa_base.hex_a_rgba(mapa_base.COLORES_REGION[r], 90)
            if r == region_activa else [190, 190, 190, 40])
    return pdk.Layer(
        "PolygonLayer", data=datos, id="areas", get_polygon="polygon",
        get_fill_color="color", get_line_color=[255, 255, 255, 255],
        stroked=True, line_width_min_pixels=1,
        pickable=region_activa is None, auto_highlight=region_activa is None)


def capa_gba(region_activa):
    """Crea el círculo que representa al Gran Buenos Aires.

    Args:
        region_activa: región seleccionada o None (vista general).

    Returns:
        Capa ScatterplotLayer con id "gba".
    """
    datos = mapa_base.tabla_gba()
    activa = region_activa in (None, "Gran Buenos Aires")
    color = mapa_base.hex_a_rgba(
        mapa_base.COLORES_REGION["Gran Buenos Aires"], 150 if activa else 40)
    datos["color"] = [color]
    datos["texto"] = ("<b>Gran Buenos Aires</b><br/>2 aglomerados"
                      "<br/><i>Clic para ver el detalle</i>")
    return pdk.Layer(
        "ScatterplotLayer", data=datos, id="gba",
        get_position="[lon, lat]", get_fill_color="color",
        get_radius=mapa_base.RADIO_GBA_METROS, radius_min_pixels=14,
        pickable=region_activa is None, auto_highlight=region_activa is None)


def capa_aglomerados(datos):
    """Crea la capa de puntos de los aglomerados, pintados por su valor.

    Args:
        datos: DataFrame con lat, lon, color y texto.

    Returns:
        Capa ScatterplotLayer con id "aglomerados".
    """
    return pdk.Layer(
        "ScatterplotLayer", data=datos, id="aglomerados",
        get_position="[lon, lat]", get_fill_color="color",
        get_line_color=[40, 40, 40], get_radius=8000, radius_min_pixels=7,
        radius_max_pixels=20, stroked=True, line_width_min_pixels=2,
        pickable=True, auto_highlight=True)


def al_clic_en_area():
    """Callback del mapa general: activa la región clickeada."""
    seleccion = st.session_state["mapa_pais"]["selection"]["objects"]
    for capa in ("areas", "gba"):
        if seleccion.get(capa):
            st.session_state["region_sel"] = seleccion[capa][0]["region"]
            return


def volver_al_pais():
    """Callback del botón "Volver": regresa a la vista general."""
    st.session_state["region_sel"] = TODO_EL_PAIS


def elegir_datos(df):
    """Dibuja los selectores de la barra lateral y arma los datos del mapa.

    Args:
        df: DataFrame de aglomerados.

    Returns:
        Tupla (datos, titulo, unidad_nota) o None si no hay datos para
        mostrar. ``datos`` tiene ``valor``, ``color`` y ``texto``.
    """
    tipo = st.sidebar.radio("Mapa", [MAPA_LABORAL, MAPA_TECNOLOGIA],
                            key="tipo_mapa")
    if tipo == MAPA_LABORAL:
        periodicidad = st.sidebar.radio(
            "Período", ["Trimestral", "Anual"], horizontal=True,
            key="periodicidad").lower()
        tabla = tabla_laboral(periodicidad)
        periodo = st.sidebar.selectbox(
            "Año" if periodicidad == "anual" else "Año y trimestre",
            mi.periodos_disponibles(tabla), key="periodo_laboral")
        indicador = st.sidebar.selectbox(
            "Indicador", list(mi.INDICADORES_LABORALES), key="ind_laboral")
        datos = mi.datos_mapa_laboral(df, tabla, periodo, indicador)
        return datos, f"{indicador} · {periodo}"
    anios = anios_tecnologia()
    if not anios:
        st.warning("No hay años con los archivos de hogares necesarios.")
        return None
    anio = st.sidebar.selectbox("Año", anios, index=len(anios) - 1,
                                key="anio_tec")
    base = base_tecnologia(anio)
    tipos = [TODOS_LOS_TIPOS, *ht.grupos_de_vivienda(
        base, config.VARIABLE_VIVIENDA_DEFECTO)]
    tipo_vivienda = st.sidebar.selectbox("Tipo de vivienda", tipos,
                                         key="tipo_vivienda")
    categorias = list(config.CATEGORIAS_CALIDAD_TEC.values())
    categoria = st.sidebar.selectbox("Calidad tecnológica (% de hogares)",
                                     categorias, key="cat_tec")
    filtro = tipo_vivienda != TODOS_LOS_TIPOS
    tabla = ht.acceso_por_aglomerado(
        base, variable=config.VARIABLE_VIVIENDA_DEFECTO if filtro else None,
        grupo=tipo_vivienda if filtro else None)
    datos = mi.datos_mapa_tecnologia(df, tabla, categoria)
    return datos, f"{categoria} · {anio} · {tipo_vivienda}"


def mostrar_leyenda(datos):
    """Dibuja la escala de colores del mapa."""
    minimo, maximo = mi.resumen_rango(datos)
    if minimo is None:
        st.warning("No hay datos para esta selección.")
        return
    desde = "rgb(%d,%d,%d)" % mi.COLOR_BAJO
    hasta = "rgb(%d,%d,%d)" % mi.COLOR_ALTO
    izq, centro, der = st.columns([1, 6, 1])
    izq.caption(f"{minimo:.1f}".replace(".", ","))
    centro.markdown(
        f'<div style="height:12px;border-radius:6px;'
        f'background:linear-gradient(to right,{desde},{hasta})"></div>',
        unsafe_allow_html=True)
    der.caption(f"{maximo:.1f}".replace(".", ","))


def main():
    """Arma la página: selectores, mapa y tabla de detalle."""
    st.set_page_config(page_title="Mapa georreferenciado", layout="wide")
    st.title("Mapa georreferenciado")
    df = obtener_datos(str(RUTA_JSON))
    areas = obtener_areas(str(RUTA_GEOJSON))
    cantidad = df.groupby("region").size()
    areas["n"] = areas["region"].map(cantidad)
    areas["texto"] = ("<b>" + areas["region"] + "</b><br/>" + areas["n"]
                      .astype(str) + " aglomerados<br/><i>Clic para ver "
                      "el detalle</i>")

    st.session_state.setdefault("region_sel", TODO_EL_PAIS)
    opciones = [TODO_EL_PAIS, *mapa_base.REGIONES_ORDEN]
    region = st.sidebar.selectbox("Región", opciones, key="region_sel")
    elegido = elegir_datos(df)
    if elegido is None:
        return
    datos, titulo = elegido
    st.subheader(titulo)
    mostrar_leyenda(datos)
    with st.expander("Convención cartográfica"):
        st.markdown(
            "Se usa la capa de provincias con los nombres oficiales del "
            "territorio argentino. Las **Islas Malvinas** y las demás islas "
            "del Atlántico Sur forman parte de la provincia de Tierra del "
            "Fuego, Antártida e Islas del Atlántico Sur y de la región "
            "**Patagonia**. El Gran Buenos Aires (CABA y partidos del "
            "conurbano) se marca con un círculo porque la capa no tiene "
            "partidos.")

    columnas_tabla = ["aglomerado", "provincia", "valor"]
    if region == TODO_EL_PAIS:
        st.caption("Hacé clic en una región para ver sus aglomerados.")
        deck = pdk.Deck(
            layers=[capa_areas(areas, None), capa_gba(None),
                    capa_aglomerados(datos)],
            initial_view_state=pdk.ViewState(latitude=-39, longitude=-64,
                                             zoom=3),
            tooltip={"html": "{texto}"}, map_style="light")
        st.pydeck_chart(deck, height=650, on_select=al_clic_en_area,
                        selection_mode="single-object", key="mapa_pais")
        with st.expander("Ver tabla de datos"):
            st.dataframe(datos[["region", *columnas_tabla]], hide_index=True)
        return

    df_region = datos[datos["region"] == region]
    contorno = mapa_base.contorno_para_zoom(areas, region)
    if contorno:
        vista = pdk.data_utils.compute_view(contorno, view_proportion=0.9)
    else:
        vista = pdk.ViewState(latitude=df_region["lat"].mean(),
                              longitude=df_region["lon"].mean(), zoom=8)
    st.button("← Volver al país", on_click=volver_al_pais)
    st.subheader(f"{region}: {len(df_region)} aglomerados")
    deck = pdk.Deck(
        layers=[capa_areas(areas, region), capa_gba(region),
                capa_aglomerados(df_region)],
        initial_view_state=vista, tooltip={"html": "{texto}"},
        map_style="light")
    evento = st.pydeck_chart(deck, height=650, on_select="rerun",
                             selection_mode="single-object",
                             key=f"mapa_{region}")
    puntos = evento.selection["objects"].get("aglomerados", [])
    if puntos:
        codigos = [p["codigo"] for p in puntos]
        st.dataframe(df_region[df_region["codigo"].isin(codigos)]
                     .drop(columns=["color", "texto", "coordenadas"]),
                     hide_index=True)
    with st.expander("Ver tabla de la región"):
        st.dataframe(df_region[columnas_tabla].sort_values(
            "valor", ascending=False), hide_index=True)


main()