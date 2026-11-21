"""Bloque D: mapas de los aglomerados EPH con los informes de las notebooks.
 
Toma los JSON que generan las notebooks de la primera etapa (carpeta
``output/``) y los ubica en el mapa con las coordenadas de los aglomerados:
 
- Mapa del Bloque B (mercado laboral y género): lee
  ``tendencias_trimestral.json`` o ``tendencias_semestral_anual.json``
  (notebook ``individuos_mercado_laboral``).
- Mapa del Bloque C (hogares y tecnología): lee ``tecnologia_informe.json``
  (notebook ``ciencia_y_tecnologia``).
 
Unión entre la EPH y el JSON de coordenadas: los informes usan el código de
aglomerado sin cero inicial ("2", "7") y el JSON de coordenadas puede traerlo
con cero ("02", "07"). Ambos lados pasan por ``normalizar_codigo`` antes de
unirse, y los aglomerados que no tengan coordenadas se informan en lugar de
perderse en silencio.
 
La página de Streamlit solo debe llamar a estas funciones y mostrar el
resultado; ``pydeck`` se importa recién al dibujar para que el resto del
módulo funcione sin él.
"""
import json
from pathlib import Path
 
import pandas as pd
 
from src import config, hogares_tecnologia as ht, rutas
from src.mercado_laboral import formatear_numero
 
# =============================================================================
# CONFIGURACIÓN
# =============================================================================
# Carpeta y archivos de la capa del mapa. El archivo de coordenadas lo
# entrega la cátedra; se aceptan los dos nombres que se usaron en el proyecto.
DIR_MAPAS = rutas.RAIZ_PROYECTO / "maps"
ARCHIVOS_COORDENADAS = ("coordenadas_aglomerados.json",
                        "aglomerados_coordenadas.json")
# Capa con los nombres oficiales de las provincias (campo "nombre").
ARCHIVO_PROVINCIAS = "provincias.geojson"
 
# Sección donde las notebooks guardan los informes de tendencias.
SECCION_TENDENCIAS = "tendencias_por_aglomerado"
 
# Períodos que puede elegir el usuario en el mapa del Bloque B: nombre ->
# archivo del informe. Para sumar el semestral alcanza con agregar una
# entrada acá y la clave en _bloques_de_periodo.
PERIODOS_MAPA_B = {
    "trimestral": config.ARCHIVO_TENDENCIAS_TRIMESTRAL,
    "anual": config.ARCHIVO_TENDENCIAS_PERIODOS,
}
 
# Indicadores del mapa B: texto que ve el usuario -> columna de la tabla.
METRICAS_MAPA_B = {
    "Tasa de desempleo total (%)": "tasa_desempleo",
    "Tasa de desempleo de varones (%)": "tasa_desempleo_varon",
    "Tasa de desempleo de mujeres (%)": "tasa_desempleo_mujer",
    "Brecha de desempleo (mujer − varón, pp)": "brecha_desempleo",
    "Población ocupada (% de la población)": "pct_ocupados",
    "Población inactiva (% de la población)": "pct_inactivos",
}
 
# Indicadores del mapa C: texto que ve el usuario -> columna de la tabla
# (los nombres vienen de ht.tabla_penetracion).
METRICAS_MAPA_C = {
    "Hogares con computadora (%)": "Computadora (%)",
    "Hogares con internet (%)": "Internet (%)",
    "Hogares con celular (%)": "Celular (%)",
}
 
# Columna que da el tamaño de cada punto (None = tamaño fijo).
COL_PESO_B = "poblacion"
COL_PESO_C = "Hogares (ponderados)"
 
# =============================================================================
# COLORES
# =============================================================================
# Paletas como lista de colores (r, g, b) de menor a mayor valor.
PALETAS = {
    "rojos": ((255, 245, 204), (253, 204, 92), (253, 141, 60),
              (227, 74, 51), (153, 0, 13)),
    "azules": ((239, 243, 255), (189, 215, 231), (107, 174, 214),
               (49, 130, 189), (8, 69, 148)),
    "verdes": ((237, 248, 233), (186, 228, 179), (116, 196, 118),
               (49, 163, 84), (0, 90, 50)),
    # Divergente centrada en 0: azul = varones, rosa = mujeres (mismos
    # colores que los gráficos del Bloque B).
    "divergente": ((31, 119, 180), (170, 200, 225), (245, 245, 245),
                   (230, 150, 180), (214, 51, 108)),
}
# Paleta de cada columna; las que no figuran usan PALETA_DEFECTO.
PALETA_DE_COLUMNA = {
    "tasa_desempleo": "rojos",
    "tasa_desempleo_varon": "rojos",
    "tasa_desempleo_mujer": "rojos",
    "brecha_desempleo": "divergente",
    "pct_ocupados": "verdes",
    "pct_inactivos": "azules",
}
PALETA_DEFECTO = "azules"
# Las paletas divergentes se centran en 0.
PALETAS_SIMETRICAS = ("divergente",)
COLOR_SIN_DATO = [190, 190, 190, 200]
ALFA_PUNTOS = 220
COLOR_PROVINCIAS = [245, 245, 245, 255]
COLOR_LIMITE_PROVINCIAS = [150, 150, 150, 255]
 
# Vista inicial: todo el país.
VISTA_PAIS = {"latitud": -40.0, "longitud": -64.0, "zoom": 3.1}
# Rango del radio de los puntos, en metros.
RADIO_MIN_M = 12000
RADIO_MAX_M = 50000
RADIO_FIJO_M = 25000
 
 
# =============================================================================
# UNIÓN ENTRE LA EPH Y LAS COORDENADAS
# =============================================================================
def normalizar_codigo(codigo):
    """Deja un código de aglomerado en una forma única, sin ceros iniciales.
 
    Es la clave de la unión: "02", "2" y 2 pasan a ser "2". Así no importa
    si el código viene de la EPH, de un informe o del JSON de coordenadas.
 
    Args:
        codigo: código del aglomerado (texto o número).
 
    Returns:
        El código como texto, sin espacios ni ceros a la izquierda.
    """
    return str(codigo).strip().lstrip("0")
 
 
def _ruta_coordenadas(directorio=None):
    """Busca el archivo de coordenadas dentro de la carpeta de mapas.
 
    Args:
        directorio: carpeta de mapas (por defecto ``DIR_MAPAS``).
 
    Returns:
        Ruta (Path) del primer archivo de ``ARCHIVOS_COORDENADAS`` que exista.
 
    Raises:
        FileNotFoundError: si no está ninguno.
    """
    directorio = Path(directorio or DIR_MAPAS)
    for nombre in ARCHIVOS_COORDENADAS:
        if (directorio / nombre).is_file():
            return directorio / nombre
    raise FileNotFoundError(
        f"No se encontró el archivo de coordenadas en {directorio} "
        f"(se busca {' o '.join(ARCHIVOS_COORDENADAS)}).")
 
 
def cargar_coordenadas(directorio=None):
    """Lee las coordenadas de los aglomerados.
 
    El JSON tiene una entrada por código de aglomerado con ``nombre`` y
    ``coordenadas`` como ``[lat, lon]``.
 
    Args:
        directorio: carpeta de mapas (por defecto ``DIR_MAPAS``).
 
    Returns:
        DataFrame con ``codigo`` (normalizado), ``aglomerado``, ``lat`` y
        ``lon``.
 
    Raises:
        FileNotFoundError: si no existe el archivo.
        ValueError: si dos entradas quedan con el mismo código normalizado.
    """
    ruta = _ruta_coordenadas(directorio)
    with open(ruta, encoding=config.ENCODING) as archivo:
        crudo = json.load(archivo)
    filas = []
    for codigo, valores in crudo.items():
        latitud, longitud = valores["coordenadas"]
        filas.append({"codigo": normalizar_codigo(codigo),
                      "aglomerado": valores.get("nombre", codigo),
                      "lat": float(latitud), "lon": float(longitud)})
    tabla = pd.DataFrame(filas)
    repetidos = tabla.loc[tabla["codigo"].duplicated(), "codigo"].tolist()
    if repetidos:
        raise ValueError(
            f"Códigos repetidos en {ruta.name} al ignorar el cero inicial: "
            f"{repetidos}")
    return tabla
 
 
def unir_con_coordenadas(datos, coordenadas, col_codigo="codigo"):
    """Agrega ``lat`` y ``lon`` a una tabla con una fila por aglomerado.
 
    La unión es por el código normalizado y conserva todas las filas de
    ``datos``; las que no tienen coordenadas se separan y se informan.
 
    Args:
        datos: DataFrame con el código de aglomerado en ``col_codigo``.
        coordenadas: resultado de ``cargar_coordenadas``.
        col_codigo: nombre de la columna con el código en ``datos``.
 
    Returns:
        Tupla ``(con_coordenadas, sin_coordenadas)``: el DataFrame de las
        filas que se pueden dibujar (con ``codigo``, ``lat`` y ``lon``) y la
        lista de códigos que no figuran en el JSON de coordenadas.
    """
    datos = datos.copy()
    datos["codigo"] = datos[col_codigo].map(normalizar_codigo)
    unido = datos.merge(coordenadas[["codigo", "lat", "lon"]], on="codigo",
                        how="left", validate="many_to_one")
    faltan = unido["lat"].isna() | unido["lon"].isna()
    sin_coordenadas = sorted(unido.loc[faltan, "codigo"].unique(),
                             key=lambda c: (len(c), c))
    return unido[~faltan].reset_index(drop=True), sin_coordenadas
 
 
# =============================================================================
# DATOS DEL BLOQUE B (JSON de tendencias)
# =============================================================================
def _leer_informe(ruta, notebook):
    """Lee un informe JSON generado por una notebook.
 
    Args:
        ruta: archivo a leer.
        notebook: notebook que lo genera (se usa en el mensaje de error).
 
    Returns:
        El contenido del JSON.
 
    Raises:
        FileNotFoundError: si el archivo no existe.
        ValueError: si el archivo no es un JSON válido.
    """
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(
            f"No se encontró {ruta.name} en {ruta.parent}. Ejecutá la "
            f"notebook {notebook} para generarlo.")
    try:
        with open(ruta, encoding=config.ENCODING) as archivo:
            return json.load(archivo)
    except json.JSONDecodeError as error:
        raise ValueError(f"{ruta.name} no es un JSON válido: {error}")
 
 
def _bloques_de_periodo(informe, tipo_periodo):
    """Devuelve los bloques por aglomerado de un informe de tendencias.
 
    El informe trimestral los guarda en ``aglomerados`` y el de períodos en
    ``semestral`` y ``anual``.
 
    Args:
        informe: sección ``tendencias_por_aglomerado`` del JSON.
        tipo_periodo: clave de ``PERIODOS_MAPA_B``.
 
    Returns:
        Diccionario código -> {nombre, periodos}.
    """
    clave = "aglomerados" if tipo_periodo == "trimestral" else tipo_periodo
    return informe.get(clave, {})
 
 
def _fila_tendencia(codigo, nombre, periodo, datos):
    """Arma la fila de un aglomerado y período a partir del informe.
 
    Args:
        codigo: código del aglomerado.
        nombre: nombre del aglomerado.
        periodo: período, por ejemplo '2024-T1' o '2024'.
        datos: tasas del período (total, por_sexo, por_rango_etario).
 
    Returns:
        Diccionario con una fila de la tabla de tendencias.
    """
    total = datos["total"]
    sexos = datos["por_sexo"]
    varon = sexos.get(config.NOMBRES_SEXO[config.SEXO_VARON], {})
    mujer = sexos.get(config.NOMBRES_SEXO[config.SEXO_MUJER], {})
    distribucion = total["distribucion_pct"]
    return {
        "codigo": codigo,
        "aglomerado_nombre": nombre,
        "periodo": periodo,
        "tasa_desempleo": total["tasa_desempleo"],
        "tasa_desempleo_varon": varon.get("tasa_desempleo"),
        "tasa_desempleo_mujer": mujer.get("tasa_desempleo"),
        "pct_ocupados": distribucion["ocupados"],
        "pct_inactivos": distribucion["inactivos"],
        "poblacion": total["poblacion"],
        "casos_muestra": total["casos_muestra"],
        "completo": datos.get("completo", True),
    }
 
 
def cargar_tendencias(tipo_periodo="trimestral", directorio=None):
    """Lee el informe de tendencias (Bloque B) y lo pasa a una tabla.
 
    Args:
        tipo_periodo: 'trimestral' o 'anual' (claves de ``PERIODOS_MAPA_B``).
        directorio: carpeta de informes (por defecto ``config.DIR_SALIDA``).
 
    Returns:
        DataFrame con una fila por período y aglomerado: ``codigo``,
        ``aglomerado_nombre``, ``periodo``, las tasas de desempleo (total,
        varones, mujeres y la brecha mujer − varón), el porcentaje de
        ocupados e inactivos, ``poblacion``, ``casos_muestra`` y
        ``completo`` (False si el período no tiene todos sus trimestres).
 
    Raises:
        ValueError: si ``tipo_periodo`` no es válido o el informe
            está vacío.
        FileNotFoundError: si no existe el informe.
    """
    if tipo_periodo not in PERIODOS_MAPA_B:
        raise ValueError(
            f"tipo_periodo debe ser uno de {list(PERIODOS_MAPA_B)}")
    carpeta = Path(directorio or config.DIR_SALIDA)
    ruta = carpeta / PERIODOS_MAPA_B[tipo_periodo]
    informe = _leer_informe(ruta, "individuos_mercado_laboral")
    bloques = _bloques_de_periodo(informe.get(SECCION_TENDENCIAS, {}),
                                  tipo_periodo)
    filas = [
        _fila_tendencia(codigo, bloque["nombre"], periodo, datos)
        for codigo, bloque in bloques.items()
        for periodo, datos in bloque["periodos"].items()
    ]
    if not filas:
        raise ValueError(f"{ruta.name} no tiene datos de aglomerados.")
    tabla = pd.DataFrame(filas)
    numericas = [c for c in tabla.columns if c.startswith(("tasa_", "pct_"))]
    numericas += ["poblacion", "casos_muestra"]
    tabla[numericas] = tabla[numericas].apply(pd.to_numeric, errors="coerce")
    tabla["brecha_desempleo"] = (tabla["tasa_desempleo_mujer"]
                                 - tabla["tasa_desempleo_varon"])
    return tabla.sort_values(["periodo", "codigo"]).reset_index(drop=True)
 
 
def periodos_disponibles(tendencias):
    """Lista los períodos de una tabla de tendencias, en orden.
 
    Args:
        tendencias: resultado de ``cargar_tendencias``.
 
    Returns:
        Lista de períodos como texto ('2024-T1', '2024-T2'...).
    """
    return sorted(tendencias["periodo"].unique())
 
 
# =============================================================================
# DATOS DEL BLOQUE C (JSON de tecnología)
# =============================================================================
def anios_disponibles_penetracion(directorio=None):
    """Lista los años del informe de tecnología.
 
    Args:
        directorio: carpeta de informes (por defecto ``config.DIR_SALIDA``).
 
    Returns:
        Lista de años como texto (vacía si no hay informe).
    """
    ruta = ht.buscar_informe_tecnologia(directorio)
    return ht.anios_del_informe(ht.cargar_informe_tecnologia(ruta))
 
 
def cargar_penetracion(anio, directorio=None):
    """Lee la penetración tecnológica por aglomerado de un año (Bloque C).
 
    Reutiliza las funciones del Bloque C para que ambas páginas lean igual
    el informe de la notebook ``ciencia_y_tecnologia``.
 
    Args:
        anio: año como texto, por ejemplo '2024'.
        directorio: carpeta de informes (por defecto ``config.DIR_SALIDA``).
 
    Returns:
        DataFrame con ``codigo``, ``aglomerado_nombre``, los hogares (muestra
        y ponderados) y el % de hogares con computadora, internet y celular.
 
    Raises:
        FileNotFoundError: si no hay informe de tecnología.
        ValueError: si el año no está en el informe.
    """
    ruta = ht.buscar_informe_tecnologia(directorio)
    informe = ht.cargar_informe_tecnologia(ruta)
    if informe is None:
        raise FileNotFoundError(
            f"No se encontró {config.PATRON_INFORME_TECNOLOGIA} en "
            f"{directorio or config.DIR_SALIDA}. Ejecutá la notebook "
            "ciencia_y_tecnologia para generarlo.")
    tabla = ht.tabla_penetracion(informe, str(anio), "aglomerado")
    if tabla.empty:
        raise ValueError(f"El informe de tecnología no tiene el año {anio}.")
    return tabla.rename(columns={"Código": "codigo",
                                 "Nombre": "aglomerado_nombre"})
 
 
# =============================================================================
# TABLAS LISTAS PARA DIBUJAR
# =============================================================================
def datos_mapa_laboral(tipo_periodo, periodo, tendencias=None,
                       coordenadas=None):
    """Prepara los datos del mapa del Bloque B para un período.
 
    Args:
        tipo_periodo: 'trimestral' o 'anual'.
        periodo: período a mostrar ('2024-T1', '2024'...).
        tendencias: resultado de ``cargar_tendencias`` (si es None se lee).
        coordenadas: resultado de ``cargar_coordenadas`` (si es None se lee).
 
    Returns:
        Tupla ``(datos, sin_coordenadas)``: tabla con una fila por
        aglomerado y coordenadas, y los códigos sin coordenadas.
 
    Raises:
        ValueError: si el período no está en el informe.
    """
    if tendencias is None:
        tendencias = cargar_tendencias(tipo_periodo)
    if coordenadas is None:
        coordenadas = cargar_coordenadas()
    elegido = tendencias[tendencias["periodo"] == periodo]
    if elegido.empty:
        raise ValueError(
            f"El período {periodo} no está en el informe "
            f"{tipo_periodo}. Disponibles: {periodos_disponibles(tendencias)}")
    return unir_con_coordenadas(elegido, coordenadas)
 
 
def datos_mapa_tecnologia(anio, penetracion=None, coordenadas=None):
    """Prepara los datos del mapa del Bloque C para un año.
 
    Args:
        anio: año como texto, por ejemplo '2024'.
        penetracion: resultado de ``cargar_penetracion`` (si es None se lee).
        coordenadas: resultado de ``cargar_coordenadas`` (si es None se lee).
 
    Returns:
        Tupla ``(datos, sin_coordenadas)``: tabla con una fila por
        aglomerado y coordenadas, y los códigos sin coordenadas.
    """
    if penetracion is None:
        penetracion = cargar_penetracion(anio)
    if coordenadas is None:
        coordenadas = cargar_coordenadas()
    return unir_con_coordenadas(penetracion, coordenadas)
 
 
# =============================================================================
# COLORES Y TAMAÑOS
# =============================================================================
def interpolar_color(posicion, paleta):
    """Devuelve el color de una paleta para una posición entre 0 y 1.
 
    Args:
        posicion: número entre 0 (primer color) y 1 (último); se recorta si
            se pasa del rango.
        paleta: lista de colores (r, g, b).
 
    Returns:
        Lista [r, g, b] con el color interpolado.
    """
    posicion = min(max(posicion, 0.0), 1.0)
    tramos = len(paleta) - 1
    indice = min(int(posicion * tramos), tramos - 1)
    fraccion = posicion * tramos - indice
    desde, hasta = paleta[indice], paleta[indice + 1]
    return [round(a + (b - a) * fraccion) for a, b in zip(desde, hasta)]
 
 
def limites_de_escala(valores, simetrica=False):
    """Calcula el mínimo y el máximo que usa la escala de colores.
 
    Args:
        valores: serie con los valores a pintar.
        simetrica: si es True la escala va de -m a +m (para brechas).
 
    Returns:
        Tupla ``(minimo, maximo)``; ``(0, 1)`` si no hay valores.
    """
    validos = pd.to_numeric(valores, errors="coerce").dropna()
    if validos.empty:
        return 0.0, 1.0
    if simetrica:
        tope = float(validos.abs().max()) or 1.0
        return -tope, tope
    return float(validos.min()), float(validos.max())
 
 
def colores_por_valor(valores, paleta, minimo, maximo, alfa=ALFA_PUNTOS):
    """Asigna un color a cada valor según su posición en la escala.
 
    Args:
        valores: serie de números.
        paleta: lista de colores (r, g, b).
        minimo: valor que recibe el primer color.
        maximo: valor que recibe el último color.
        alfa: opacidad de 0 a 255.
 
    Returns:
        Lista de [r, g, b, alfa]; los valores faltantes reciben
        ``COLOR_SIN_DATO``.
    """
    rango = maximo - minimo
    colores = []
    for valor in pd.to_numeric(valores, errors="coerce"):
        if pd.isna(valor):
            colores.append(list(COLOR_SIN_DATO))
            continue
        posicion = (valor - minimo) / rango if rango else 0.5
        colores.append(interpolar_color(posicion, paleta) + [alfa])
    return colores
 
 
def radios_por_peso(pesos):
    """Calcula el radio de cada punto en metros según su peso.
 
    Los puntos crecen con la raíz cuadrada del peso, así el área es
    proporcional a la población (o a los hogares).
 
    Args:
        pesos: serie de números, o None para usar un radio fijo.
 
    Returns:
        Lista de radios, entre ``RADIO_MIN_M`` y ``RADIO_MAX_M``.
    """
    if pesos is None:
        return None
    pesos = pd.to_numeric(pesos, errors="coerce").fillna(0).clip(lower=0)
    maximo = pesos.max()
    if maximo <= 0:
        return [RADIO_FIJO_M] * len(pesos)
    relativo = (pesos / maximo) ** 0.5
    return (RADIO_MIN_M + (RADIO_MAX_M - RADIO_MIN_M) * relativo).tolist()
 
 
def preparar_puntos(datos, col_valor, etiqueta, col_peso=None,
                    col_detalle=None):
    """Agrega a la tabla las columnas que usa la capa de puntos.
 
    Args:
        datos: tabla con una fila por aglomerado, ``lat`` y ``lon``.
        col_valor: columna que se pinta.
        etiqueta: nombre del indicador (se muestra en el cartel).
        col_peso: columna que define el tamaño del punto (None = fijo).
        col_detalle: columna de texto con información extra para el cartel
            (None = sin detalle).
 
    Returns:
        Copia de ``datos`` con ``color``, ``radio``, ``indicador``,
        ``valor_texto`` y ``detalle``.
    """
    nombre_paleta = PALETA_DE_COLUMNA.get(col_valor, PALETA_DEFECTO)
    simetrica = nombre_paleta in PALETAS_SIMETRICAS
    minimo, maximo = limites_de_escala(datos[col_valor], simetrica)
    puntos = datos.copy()
    puntos["color"] = colores_por_valor(
        puntos[col_valor], PALETAS[nombre_paleta], minimo, maximo)
    pesos = puntos[col_peso] if col_peso else None
    puntos["radio"] = radios_por_peso(pesos) or RADIO_FIJO_M
    puntos["indicador"] = etiqueta
    puntos["valor_texto"] = [formatear_numero(v, simetrica)
                             for v in pd.to_numeric(puntos[col_valor],
                                                    errors="coerce")]
    puntos["detalle"] = puntos[col_detalle] if col_detalle else ""
    return puntos
 
 
def agregar_detalle_laboral(datos):
    """Agrega el texto de detalle que se muestra en el cartel del mapa B.
 
    Args:
        datos: tabla de ``datos_mapa_laboral``.
 
    Returns:
        Copia de ``datos`` con la columna ``detalle`` (período, población y
        casos de muestra, y aviso si el período está incompleto).
    """
    datos = datos.copy()
    datos["detalle"] = [
        f"Período: {fila.periodo} | Población: {fila.poblacion:,.0f} | "
        f"Casos: {fila.casos_muestra:,.0f}".replace(",", ".")
        + ("" if fila.completo else " | Período incompleto")
        for fila in datos.itertuples()
    ]
    return datos
 
 
def agregar_detalle_tecnologia(datos):
    """Agrega el texto de detalle que se muestra en el cartel del mapa C.
 
    Args:
        datos: tabla de ``datos_mapa_tecnologia``.
 
    Returns:
        Copia de ``datos`` con la columna ``detalle`` (los tres indicadores
        y la cantidad de hogares de la muestra).
    """
    datos = datos.copy()
    columnas = ["Computadora (%)", "Internet (%)", "Celular (%)",
                "Hogares (muestra)"]
    datos["detalle"] = [
        f"Computadora: {formatear_numero(pc)}% | Internet: "
        f"{formatear_numero(internet)}% | Celular: "
        f"{formatear_numero(celular)}% | Hogares (muestra): {muestra}"
        for pc, internet, celular, muestra in datos[columnas].itertuples(
            index=False)
    ]
    return datos
 
 
# =============================================================================
# MAPA (pydeck)
# =============================================================================
def _cargar_provincias(directorio=None):
    """Lee la capa de provincias si está disponible.
 
    Args:
        directorio: carpeta de mapas (por defecto ``DIR_MAPAS``).
 
    Returns:
        El GeoJSON como diccionario, o None si el archivo no existe.
    """
    ruta = Path(directorio or DIR_MAPAS) / ARCHIVO_PROVINCIAS
    if not ruta.is_file():
        return None
    with open(ruta, encoding=config.ENCODING) as archivo:
        return json.load(archivo)
 
 
def construir_mapa(puntos, directorio_mapas=None):
    """Arma el mapa con un punto por aglomerado.
 
    Si existe ``provincias.geojson`` se dibuja debajo como capa con los
    nombres oficiales de las provincias.
 
    Args:
        puntos: resultado de ``preparar_puntos``.
        directorio_mapas: carpeta de mapas (por defecto ``DIR_MAPAS``).
 
    Returns:
        Objeto ``pydeck.Deck`` listo para ``st.pydeck_chart``.
    """
    import pydeck as pdk  # se importa acá para no exigirlo al resto
 
    capas = []
    provincias = _cargar_provincias(directorio_mapas)
    if provincias is not None:
        capas.append(pdk.Layer(
            "GeoJsonLayer", data=provincias, id="provincias",
            get_fill_color=COLOR_PROVINCIAS,
            get_line_color=COLOR_LIMITE_PROVINCIAS,
            stroked=True, filled=True, line_width_min_pixels=1,
            pickable=False))
    capas.append(pdk.Layer(
        "ScatterplotLayer", data=puntos, id="aglomerados",
        get_position="[lon, lat]",  # pydeck usa el orden [lon, lat]
        get_fill_color="color", get_line_color=[255, 255, 255],
        get_radius="radio", radius_min_pixels=6, radius_max_pixels=40,
        stroked=True, line_width_min_pixels=1, pickable=True,
        auto_highlight=True))
    return pdk.Deck(
        layers=capas,
        initial_view_state=pdk.ViewState(
            latitude=VISTA_PAIS["latitud"], longitude=VISTA_PAIS["longitud"],
            zoom=VISTA_PAIS["zoom"]),
        tooltip={"html": (
            "<b>{aglomerado_nombre}</b><br/>{indicador}: "
            "<b>{valor_texto}</b><br/><small>{detalle}</small>")},
        map_style="light")
 
 
def mapa_laboral(datos, metrica, directorio_mapas=None):
    """Arma el mapa del Bloque B para un indicador.
 
    Args:
        datos: resultado de ``datos_mapa_laboral``.
        metrica: texto de ``METRICAS_MAPA_B``.
        directorio_mapas: carpeta de mapas (por defecto ``DIR_MAPAS``).
 
    Returns:
        Objeto ``pydeck.Deck``.
    """
    puntos = preparar_puntos(
        agregar_detalle_laboral(datos), METRICAS_MAPA_B[metrica], metrica,
        col_peso=COL_PESO_B, col_detalle="detalle")
    return construir_mapa(puntos, directorio_mapas)
 
 
def mapa_tecnologia(datos, metrica, directorio_mapas=None):
    """Arma el mapa del Bloque C para un indicador.
 
    Args:
        datos: resultado de ``datos_mapa_tecnologia``.
        metrica: texto de ``METRICAS_MAPA_C``.
        directorio_mapas: carpeta de mapas (por defecto ``DIR_MAPAS``).
 
    Returns:
        Objeto ``pydeck.Deck``.
    """
    puntos = preparar_puntos(
        agregar_detalle_tecnologia(datos), METRICAS_MAPA_C[metrica], metrica,
        col_peso=COL_PESO_C, col_detalle="detalle")
    return construir_mapa(puntos, directorio_mapas)
 
 
# =============================================================================
# DESCRIPCIÓN DE LOS RESULTADOS
# =============================================================================
def describir_extremos(datos, col_valor, etiqueta, con_signo=False):
    """Escribe en frases el aglomerado más alto, el más bajo y el promedio.
 
    El promedio es simple (un voto por aglomerado), no ponderado.
 
    Args:
        datos: tabla con ``aglomerado_nombre`` y la columna a describir.
        col_valor: columna del indicador.
        etiqueta: nombre del indicador.
        con_signo: si es True muestra el signo en los positivos (brechas).
 
    Returns:
        Lista de frases; vacía si no hay valores.
    """
    validos = datos.dropna(subset=[col_valor])
    if validos.empty:
        return []
    mayor = validos.loc[validos[col_valor].idxmax()]
    menor = validos.loc[validos[col_valor].idxmin()]
    promedio = validos[col_valor].mean()
    return [
        f"{etiqueta}: el valor más alto es de {mayor['aglomerado_nombre']} "
        f"({formatear_numero(mayor[col_valor], con_signo)}) y el más bajo, "
        f"de {menor['aglomerado_nombre']} "
        f"({formatear_numero(menor[col_valor], con_signo)}).",
        f"El promedio simple de los {len(validos)} aglomerados con datos es "
        f"{formatear_numero(promedio, con_signo)}.",
    ]
 