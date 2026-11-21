"""
Construcción del DataFrame de aglomerados EPH para el mapa.

Lee el archivo `aglomerados_coordenadas.json` y le agrega la región y la
provincia de cada aglomerado, siguiendo la clasificación regional de la EPH
(INDEC). El resultado queda ordenado por región y por nombre de aglomerado.
"""

import pandas as pd


# Región y provincia por código de aglomerado EPH.
# Formato: "código": (región, provincia)
# Nota: en la EPH, "Gran Buenos Aires" como región incluye solo CABA y los
# Partidos del GBA; el resto de los aglomerados bonaerenses va en "Pampeana".


REGION_PROVINCIA = {
    # Gran Buenos Aires
    "32": ("Gran Buenos Aires", "CABA"),
    "33": ("Gran Buenos Aires", "Buenos Aires"),
    # Noroeste
    "18": ("Noroeste", "Santiago del Estero"),
    "19": ("Noroeste", "Jujuy"),
    "22": ("Noroeste", "Catamarca"),
    "23": ("Noroeste", "Salta"),
    "25": ("Noroeste", "La Rioja"),
    "29": ("Noroeste", "Tucumán"),
    # Noreste
    "07": ("Noreste", "Misiones"),
    "08": ("Noreste", "Chaco"),
    "12": ("Noreste", "Corrientes"),
    "15": ("Noreste", "Formosa"),
    # Cuyo
    "10": ("Cuyo", "Mendoza"),
    "26": ("Cuyo", "San Luis"),
    "27": ("Cuyo", "San Juan"),
    # Pampeana (incluye Entre Ríos y los aglomerados bonaerenses fuera del GBA)
    "02": ("Pampeana", "Buenos Aires"),
    "03": ("Pampeana", "Buenos Aires"),
    "34": ("Pampeana", "Buenos Aires"),
    "38": ("Pampeana", "Buenos Aires"),
    "04": ("Pampeana", "Santa Fe"),
    "05": ("Pampeana", "Santa Fe"),
    "06": ("Pampeana", "Entre Ríos"),
    "14": ("Pampeana", "Entre Ríos"),
    "13": ("Pampeana", "Córdoba"),
    "36": ("Pampeana", "Córdoba"),
    "30": ("Pampeana", "La Pampa"),
    # Patagonia
    "09": ("Patagonia", "Chubut"),
    "91": ("Patagonia", "Chubut"),
    "17": ("Patagonia", "Neuquén"),
    "20": ("Patagonia", "Santa Cruz"),
    "31": ("Patagonia", "Tierra del Fuego"),
    "93": ("Patagonia", "Río Negro"),
}


def normalizar_codigo(codigo):
    """Devuelve el código de aglomerado con dos dígitos ('2' -> '02').

    Los resultados de los bloques B y C traen el código sin cero a la
    izquierda y el JSON de coordenadas lo trae con cero; esta función deja
    ambos en el mismo formato para poder unirlos.

    Args:
        codigo: código de aglomerado (texto o número).

    Returns:
        Texto de dos dígitos.
    """
    return str(codigo).strip().zfill(2)


def cargar_aglomerados(ruta) -> pd.DataFrame:
    """Construye el DataFrame de aglomerados EPH para el mapa.

    Lee el archivo JSON de aglomerados (cada clave es el código EPH y cada
    valor contiene ``nombre`` y ``coordenadas`` como ``[lat, lon]``), le asocia
    su región y provincia según ``REGION_PROVINCIA`` y devuelve el resultado
    ordenado por región y nombre de aglomerado.

    Args:
        ruta: Ruta al archivo JSON de aglomerados (``str`` o ``pathlib.Path``).

    Returns:
        DataFrame con las columnas ``codigo``, ``aglomerado``, ``region``,
        ``provincia``, ``lat`` y ``lon``, ordenado por ``region`` y
        ``aglomerado`` con índice reiniciado.
    """
    df = pd.read_json(
        ruta,
        orient="index",
        encoding="utf-8",
        dtype={
            "index": str})
    df.index = df.index.astype(str).str.zfill(
        2)  # evita que pd.read_json reinterprete
    # el "02","03 etc a "2","3"
    df.index.name = "codigo"
    df = df.reset_index()

    df[["lat", "lon"]] = pd.DataFrame(
        df["coordenadas"].tolist(), index=df.index)
    df[["region", "provincia"]] = pd.DataFrame(
        df["codigo"].map(REGION_PROVINCIA).tolist(), index=df.index
    )

    columnas = ["codigo", "aglomerado", "region", "provincia", "lat", "lon"]
    return (
        df.rename(columns={"nombre": "aglomerado"})[columnas]
        .sort_values(["region", "aglomerado"], ignore_index=True)
    )
