"""Mapa base de Argentina: regiones EPH, aglomerados e islas del Atlántico Sur.

Convención cartográfica del proyecto
------------------------------------
* La capa de provincias (``maps/provincias.geojson``) usa los nombres oficiales
  del territorio argentino. La provincia de Tierra del Fuego, Antártida e Islas
  del Atlántico Sur incluye las Islas Malvinas, y se asigna a la región
  Patagonia.
* La vista principal se recorta a ``RECORTE``: conserva el territorio
  continental, Tierra del Fuego y las Islas Malvinas, y deja afuera la
  Antártida y las Georgias y Sandwich del Sur (fuera del cuadro del mapa).
* La región "Gran Buenos Aires" de la EPH es solo CABA y los partidos del
  conurbano. La capa provincial no tiene partidos, así que la provincia de
  Buenos Aires se pinta como Pampeana (allí están La Plata, Bahía Blanca, Mar
  del Plata, etc.) y el Gran Buenos Aires se marca con un círculo.
"""
import geopandas as gpd
import pandas as pd

REGIONES_ORDEN = ("Gran Buenos Aires", "Noroeste", "Noreste", "Cuyo",
                  "Pampeana", "Patagonia")

COLORES_REGION = {
    "Gran Buenos Aires": "#1f77b4",
    "Noroeste": "#d62728",
    "Noreste": "#2ca02c",
    "Cuyo": "#9467bd",
    "Pampeana": "#ff7f0e",
    "Patagonia": "#17becf",
}

# Región de cada provincia, con los nombres exactos del GeoJSON (campo
# "nombre").
PROVINCIA_A_REGION = {
    "Ciudad Autónoma de Buenos Aires": "Gran Buenos Aires",
    "Buenos Aires": "Pampeana",
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

# (lon_min, lat_min, lon_max, lat_max): continente, T. del Fuego, Malvinas.
RECORTE = (-74.0, -56.0, -53.0, -21.0)
# Partes con menos superficie (grados cuadrados) se descartan (islotes).
AREA_MINIMA = 0.05
SIMPLIFICACION = 0.02
# Las partes de Patagonia que están todas al este de esta longitud son islas
# (Malvinas): no se usan para encuadrar el zoom de la región.
LON_ISLAS = -63.0
# Círculo que representa al Gran Buenos Aires.
CENTRO_GBA = (-34.62, -58.45)
RADIO_GBA_METROS = 30000


def hex_a_rgba(color_hex, alfa=255):
    """Convierte un color hexadecimal a [r, g, b, alfa] (formato de pydeck).

    Args:
        color_hex: color como "#rrggbb".
        alfa: opacidad de 0 (transparente) a 255 (opaco).

    Returns:
        Lista [r, g, b, alfa].
    """
    h = color_hex.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [alfa]


def construir_areas(ruta_geojson):
    """Construye un área por región uniendo las provincias del GeoJSON.

    Asigna la región a cada provincia, recorta lo que queda fuera del cuadro
    del mapa, une las provincias de cada región, simplifica el contorno y
    separa el resultado en polígonos (el formato que pide pydeck).

    Args:
        ruta_geojson: ruta a ``provincias.geojson``.

    Returns:
        DataFrame con una fila por polígono y columnas ``region`` y
        ``polygon`` (lista de coordenadas [lon, lat] del contorno exterior).

    Raises:
        ValueError: si alguna provincia del GeoJSON no está en
            ``PROVINCIA_A_REGION``.
    """
    gdf = gpd.read_file(ruta_geojson)
    gdf["region"] = gdf["nombre"].map(PROVINCIA_A_REGION)
    sin_region = gdf.loc[gdf["region"].isna(), "nombre"].tolist()
    if sin_region:
        raise ValueError(f"Provincias sin región asignada: {sin_region}")
    gdf["geometry"] = gdf.geometry.clip_by_rect(*RECORTE)
    gdf = gdf[~gdf.geometry.is_empty]
    geometrias = gdf.dissolve(by="region").geometry.simplify(SIMPLIFICACION)
    filas = []
    for region, geom in geometrias.items():
        for parte in getattr(geom, "geoms", [geom]):
            if parte.area >= AREA_MINIMA:
                filas.append({"region": region, "polygon": [
                    list(c) for c in parte.exterior.coords]})
    return pd.DataFrame(filas)


def contorno_para_zoom(areas, region):
    """Devuelve las coordenadas que se usan para encuadrar una región.

    En Patagonia se dejan afuera las islas (Malvinas) para que el zoom
    muestre el continente; las islas igual se dibujan en el mapa.

    Args:
        areas: resultado de construir_areas.
        region: nombre de la región.

    Returns:
        Lista de coordenadas [lon, lat] (vacía si la región no tiene
        polígono, como Gran Buenos Aires).
    """
    coordenadas = []
    for poligono in areas.loc[areas["region"] == region, "polygon"]:
        if region == "Patagonia" and min(c[0] for c in poligono) > LON_ISLAS:
            continue
        coordenadas.extend(poligono)
    return coordenadas


def tabla_gba():
    """Arma la fila del círculo que representa al Gran Buenos Aires.

    Returns:
        DataFrame de una fila con region, lat y lon.
    """
    return pd.DataFrame([{"region": "Gran Buenos Aires",
                          "lat": CENTRO_GBA[0], "lon": CENTRO_GBA[1]}])
