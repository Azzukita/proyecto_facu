"""
Página de mapas con pydeck: áreas por región y aglomerados dentro de cada una.

Vista general: seis áreas (una por región) que se pueden seleccionar con un
clic. Al seleccionar una región, el mapa hace zoom sobre ella y muestra sus
aglomerados EPH como puntos seleccionables.
"""

from pathlib import Path
import sys

import geopandas as gpd
import pandas as pd
import pydeck as pdk
import streamlit as st

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent.parent
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from src import regiones  # noqa: E402

TODO_EL_PAIS = "Todo el país"

# Color fijo por región (hex)
COLORES_REGION = {
    "Buenos Aires": "#1f77b4",
    "Noroeste": "#d62728",
    "Noreste": "#2ca02c",
    "Cuyo": "#9467bd",
    "Pampeana": "#ff7f0e",
    "Patagonia": "#17becf",
}

# Región de cada provincia, usando los nombres exactos del GeoJSON (campo "nombre")
PROVINCIA_A_REGION = {
    "Ciudad Autónoma de Buenos Aires": "Buenos Aires",
    "Buenos Aires": "Buenos Aires",
    "Jujuy": "Noroeste",
    "Salta": "Noroeste",
    "Tucumán": "Noroeste",
    "Catamarca": "Noroeste",
    "La Rioja": "Noroeste",
    "Santiago del Estero": "Noroeste",
    "Misiones": "Noreste",
    "Corrientes": "Noreste",
    "Chaco": "Noreste",
    "Formosa": "Noreste",
    "Mendoza": "Cuyo",
    "San Juan": "Cuyo",
    "San Luis": "Cuyo",
    "Santa Fe": "Pampeana",
    "Córdoba": "Pampeana",
    "Entre Ríos": "Pampeana",
    "La Pampa": "Pampeana",
    "Neuquén": "Patagonia",
    "Río Negro": "Patagonia",
    "Chubut": "Patagonia",
    "Santa Cruz": "Patagonia",
    "Tierra del Fuego, Antártida e Islas del Atlántico Sur": "Patagonia",
}

# El GeoJSON de Tierra del Fuego incluye la Antártida y las islas del Atlántico
# Sur (llega hasta la latitud -90). Se recorta a este rectángulo para quedarse
# con el territorio continental, Tierra del Fuego y las Malvinas.
# Formato: (lon_min, lat_min, lon_max, lat_max)
RECORTE = (-74.0, -56.0, -53.0, -21.0)

# Las partes con menos superficie (en grados cuadrados) se descartan: son
# islotes que solo agregan peso al mapa.
AREA_MINIMA = 0.05


def hex_a_rgba(color_hex, alfa = 255):
    """Convierte un color hexadecimal a [r, g, b, alfa] (formato de pydeck).

    Args:
        color_hex: Color como "#rrggbb".
        alfa: Opacidad de 0 (transparente) a 255 (opaco).

    Returns:
        Lista [r, g, b, alfa].
    """
    h = color_hex.lstrip("#")
    return [int(h[i : i + 2], 16) for i in (0, 2, 4)] + [alfa]


@st.cache_data
def obtener_datos(ruta_json):
    """Carga el DataFrame de aglomerados y lo cachea."""
    return regiones.cargar_aglomerados(ruta_json)


@st.cache_data
def obtener_areas(ruta_geojson):
    """Construye un área por región uniendo las provincias del GeoJSON.

    Pasos: asigna región a cada provincia, recorta lo que queda fuera del
    territorio argentino, une las provincias de cada región, simplifica el
    contorno y separa el resultado en polígonos (formato que pide pydeck).

    Args:
        ruta_geojson: Ruta a `provincias.geojson`.

    Returns:
        DataFrame con una fila por polígono y columnas `region` y `polygon`
        (lista de coordenadas [lon, lat] del contorno exterior).

    Raises:
        ValueError: si alguna provincia del GeoJSON no está en
            `PROVINCIA_A_REGION`.
    """
    gdf = gpd.read_file(ruta_geojson)
    gdf["region"] = gdf["nombre"].map(PROVINCIA_A_REGION)

    # Falla de forma explícita en lugar de perder provincias sin avisar
    sin_region = gdf.loc[gdf["region"].isna(), "nombre"].tolist()
    if sin_region:
        raise ValueError(f"Provincias sin región asignada: {sin_region}")

    gdf["geometry"] = gdf.geometry.clip_by_rect(*RECORTE)
    gdf = gdf[~gdf.geometry.is_empty]

    # Une las provincias de cada región y simplifica para aligerar el mapa
    por_region = gdf.dissolve(by="region")
    geometrias = por_region.geometry.simplify(0.02)

    # pydeck dibuja un polígono por fila: se separan los multipolígonos
    filas = []
    for region, geom in geometrias.items():
        for parte in getattr(geom, "geoms", [geom]):
            if parte.area >= AREA_MINIMA:
                filas.append(
                    {"region": region, "polygon": [list(c) for c in parte.exterior.coords]}
                )
    return pd.DataFrame(filas)


def capa_areas(areas, region_activa):
    """Crea la capa de áreas de las regiones.

    Args:
        areas: DataFrame de `obtener_areas` con la columna `n` (aglomerados).
        region_activa: Región seleccionada, o None en la vista general. En la
            vista general las áreas son clickeables; con una región activa,
            esa se resalta, las demás se apagan y ninguna es clickeable.

    Returns:
        Capa PolygonLayer con id "areas".
    """
    datos = areas.copy()
    if region_activa is None:
        datos["color"] = datos["region"].map(lambda r: hex_a_rgba(COLORES_REGION[r], 150))
    else:
        datos["color"] = datos["region"].map(
            lambda r: hex_a_rgba(COLORES_REGION[r], 90) if r == region_activa else [190, 190, 190, 40]
        )
    return pdk.Layer(
        "PolygonLayer",
        data=datos,
        id="areas",
        get_polygon="polygon",
        get_fill_color="color",
        get_line_color=[255, 255, 255, 255],
        stroked=True,
        line_width_min_pixels=1,
        pickable=region_activa is None,
        auto_highlight=region_activa is None,
    )


def capa_aglomerados(data_frame):
    """Crea la capa de puntos con los aglomerados de una región.

    Args:
        df: DataFrame con aglomerado, provincia, region, lat y lon.

    Returns:
        Capa ScatterplotLayer con id "aglomerados", clickeable.
    """
    datos = data_frame.copy()
    datos["color"] = datos["region"].map(lambda r: hex_a_rgba(COLORES_REGION[r]))
    return pdk.Layer(
        "ScatterplotLayer",
        data=datos,
        id="aglomerados",
        get_position="[lon, lat]",  # pydeck usa el orden [lon, lat]
        get_fill_color="color",
        get_line_color=[255, 255, 255],
        get_radius=8000,  # en metros
        radius_min_pixels=7,
        radius_max_pixels=20,
        stroked=True,
        line_width_min_pixels=2,
        pickable=True,
        auto_highlight=True,
    )


def al_clic_en_area():
    """Callback del mapa general: activa la región clickeada.

    Corre antes de re-ejecutar el script, por lo que puede modificar el valor
    del selector de la barra lateral sin conflicto.
    """
    objetos = st.session_state["mapa_pais"]["selection"]["objects"].get("areas", [])
    if objetos:
        st.session_state["region_sel"] = objetos[0]["region"]


def volver_al_pais():
    """Callback del botón "Volver": regresa a la vista general."""
    st.session_state["region_sel"] = TODO_EL_PAIS


def main() :
    """Arma la página: selector de región, mapa y tabla de selección."""
    st.set_page_config(page_title="Aglomerados EPH", layout="wide")
    st.title("Mapa de Aglomerados EPH (INDEC)")

    df = obtener_datos(str(RAIZ_PROYECTO / "maps" / "aglomerados_coordenadas.json"))
    areas = obtener_areas(str(RAIZ_PROYECTO / "maps" / "provincias.geojson"))
    areas["n"] = areas["region"].map(df.groupby("region").size())  # aglomerados por región

    # Estado inicial y selector de región (se sincroniza con los clics del mapa)
    st.session_state.setdefault("region_sel", TODO_EL_PAIS)
    opciones = [TODO_EL_PAIS, *sorted(df["region"].unique())]
    region = st.sidebar.selectbox("Región", opciones, key="region_sel")

    if region == TODO_EL_PAIS:
        st.caption("Hacé clic en una región para ver sus aglomerados.")
        deck = pdk.Deck(
            layers=[capa_areas(areas, None)],
            initial_view_state=pdk.ViewState(latitude=-39, longitude=-64, zoom=3),
            tooltip={
                "html": "<b>{region}</b><br/>{n} aglomerados<br/><i>Clic para ver el detalle</i>"
            },
            map_style="light",
        )
        st.pydeck_chart(
            deck,
            height=650,
            on_select=al_clic_en_area,
            selection_mode="single-object",
            key="mapa_pais",
        )
        with st.expander("Ver tabla de datos"):
            st.dataframe(df, hide_index=True)
        return

    # Vista de una región: zoom al área y puntos de sus aglomerados
    df_region = df[df["region"] == region]
    contorno = [c for poly in areas.loc[areas["region"] == region, "polygon"] for c in poly]
    vista = pdk.data_utils.compute_view(contorno, view_proportion=0.9)

    st.button("← Volver al país", on_click=volver_al_pais)
    st.subheader(f"{region}: {len(df_region)} aglomerados")

    deck = pdk.Deck(
        layers=[capa_areas(areas, region), capa_aglomerados(df_region)],
        initial_view_state=vista,
        tooltip={"html": "<b>{aglomerado}</b><br/>{provincia}<br/>Región: {region}"},
        map_style="light",
    )
    evento = st.pydeck_chart(
        deck,
        height=650,
        on_select="rerun",
        selection_mode="single-object",
        key=f"mapa_{region}",  # clave distinta por región para no arrastrar selecciones
    )

    # Detalle del aglomerado seleccionado
    puntos = evento.selection["objects"].get("aglomerados", [])
    if puntos:
        st.dataframe(
            df_region[df_region["codigo"].isin([p["codigo"] for p in puntos])],
            hide_index=True,
        )

    with st.expander("Ver tabla de la región"):
        st.dataframe(df_region, hide_index=True)


main()