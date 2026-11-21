"""Bloque C (segunda etapa): tecnología y condiciones de habitabilidad.

Todo el cálculo de la página "Hogares y Tecnología" vive acá, con pandas. La
página de Streamlit solo llama a estas funciones y dibuja el resultado.

Tiene dos partes:

1. Lectura de los informes de penetración tecnológica de la primera etapa
   (JSON en ``output/``).
2. Cruce de los hogares del módulo TIC con los hogares de Mercado Laboral
   para relacionar la calidad tecnológica con la vivienda.
"""
import json

import pandas as pd

from src import config, data_loader

# Nombres de las columnas calculadas (se usan en tablas, gráficos y CSV).
COL_REGION = "REGION_COD"
COL_CALIDAD = "CALIDAD_TEC"
COL_PESO = "PESO"
COL_TIENE_PC = "TIENE_PC"
COL_TIENE_INTERNET = "TIENE_INTERNET"
COLS_CLAVE = list(config.COLS_ID_HOGAR)

# Columnas de la tabla de resultados (lo que se muestra y se descarga).
COL_GRUPO = "Grupo de vivienda"
COL_CATEGORIA = "Calidad tecnológica"
COL_MUESTRA = "Hogares (muestra)"
COL_EXPANDIDOS = "Hogares (ponderados)"
COL_PORCENTAJE = "Porcentaje (%)"


# =============================================================================
# INFORMES DE PENETRACIÓN TECNOLÓGICA (JSON de la primera etapa)
# =============================================================================
def buscar_informe_tecnologia(directorio=None):
    """Busca el informe de tecnología más reciente.

    La primera etapa puede guardar varios archivos (con fecha y hora en el
    nombre si el informe ya existía), así que se toma el último por nombre.

    Args:
        directorio: carpeta de informes (por defecto config.DIR_SALIDA).

    Returns:
        Ruta (Path) del informe, o None si no hay ninguno.
    """
    directorio = directorio or config.DIR_SALIDA
    candidatos = sorted(directorio.glob(config.PATRON_INFORME_TECNOLOGIA))
    return candidatos[-1] if candidatos else None


def cargar_informe_tecnologia(ruta=None):
    """Lee el informe de penetración tecnológica de la primera etapa.

    Args:
        ruta: archivo a leer (por defecto, el más reciente de la carpeta
            de informes).

    Returns:
        El informe como diccionario, o None si no existe o está dañado.
    """
    ruta = ruta or buscar_informe_tecnologia()
    if ruta is None:
        return None
    try:
        with open(ruta, encoding=config.ENCODING) as archivo:
            return json.load(archivo)
    except (OSError, json.JSONDecodeError):
        return None


def anios_del_informe(informe):
    """Lista los años disponibles en el informe, ordenados.

    Args:
        informe: diccionario devuelto por cargar_informe_tecnologia.

    Returns:
        Lista de años como texto (vacía si el informe no tiene años).
    """
    return sorted((informe or {}).get("anios", {}))


def _clave_nivel(nivel):
    """Devuelve la clave del informe para 'region' o 'aglomerado'."""
    if nivel not in ("region", "aglomerado"):
        raise ValueError("nivel debe ser 'region' o 'aglomerado'")
    return "por_" + nivel


def tabla_penetracion(informe, anio, nivel):
    """Arma la tabla de penetración tecnológica de un año.

    Args:
        informe: diccionario del informe de tecnología.
        anio: año como texto, por ejemplo '2024'.
        nivel: 'region' o 'aglomerado'.

    Returns:
        DataFrame con una fila por región o aglomerado: Código, Nombre,
        hogares (muestra y ponderados) y el % de hogares con computadora,
        internet y celular. Vacío si el año no está en el informe.
    """
    bloques = informe.get("anios", {}).get(anio, {}).get(_clave_nivel(nivel))
    if not bloques:
        return pd.DataFrame()
    tabla = pd.DataFrame.from_dict(bloques, orient="index")
    tabla.index.name = "Código"
    tabla = tabla.reset_index()
    tabla = tabla.rename(columns={
        "nombre": "Nombre",
        "hogares_muestra": "Hogares (muestra)",
        "hogares_ponderados": "Hogares (ponderados)",
        "pct_computadora": "Computadora (%)",
        "pct_internet": "Internet (%)",
        "pct_celular": "Celular (%)",
    })
    columnas = ["Código", "Nombre", "Hogares (muestra)",
                "Hogares (ponderados)", "Computadora (%)", "Internet (%)",
                "Celular (%)"]
    return tabla[columnas]


def opciones_por_defecto(tabla, nivel):
    """Elige qué grupos geográficos se preseleccionan.

    Regiones: todas (son pocas). Aglomerados: los de más hogares
    ponderados (config.N_AGLOMERADOS_DEFECTO), para que el gráfico no
    arranque con 32 barras.

    Args:
        tabla: resultado de tabla_penetracion.
        nivel: 'region' o 'aglomerado'.

    Returns:
        Lista de nombres a preseleccionar.
    """
    if tabla.empty:
        return []
    if nivel == "region":
        return tabla["Nombre"].tolist()
    mayores = tabla.nlargest(config.N_AGLOMERADOS_DEFECTO,
                             "Hogares (ponderados)")
    return mayores["Nombre"].tolist()


def filtrar_penetracion(tabla, nombres):
    """Deja solo los grupos geográficos elegidos.

    Args:
        tabla: resultado de tabla_penetracion.
        nombres: lista de nombres de región o aglomerado.

    Returns:
        DataFrame filtrado (mismas columnas), con índice reiniciado.
    """
    return tabla[tabla["Nombre"].isin(nombres)].reset_index(drop=True)


# =============================================================================
# CRUCE DE HOGARES (TIC + VIVIENDA)
# =============================================================================
def leer_columnas_hogares(ruta, columnas):
    """Lee solo algunas columnas de un archivo de hogares con pandas.

    Todo se lee como texto (dtype=str) para no perder ceros ni confundir
    códigos, y 'NA' se conserva como texto. Se prueban las codificaciones de
    config.ENCODINGS_ALTERNATIVOS si la principal falla.

    Args:
        ruta: ruta al archivo.
        columnas: nombres de las columnas a leer.

    Returns:
        DataFrame con esas columnas.

    Raises:
        ValueError: si el archivo no tiene alguna de las columnas pedidas
            o no se pudo decodificar.
    """
    codificaciones = [config.ENCODING, *config.ENCODINGS_ALTERNATIVOS]
    for codificacion in codificaciones:
        try:
            encabezado = pd.read_csv(ruta, sep=config.SEPARADOR, nrows=0,
                                     encoding=codificacion).columns
            faltan = [c for c in columnas if c not in encabezado]
            if faltan:
                raise ValueError(
                    f"{ruta.name} no tiene las columnas: {', '.join(faltan)}")
            return pd.read_csv(ruta, sep=config.SEPARADOR, dtype=str,
                               keep_default_na=False, usecols=list(columnas),
                               encoding=codificacion)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"No se pudo leer {ruta} con {codificaciones}")


def normalizar_clave(df):
    """Normaliza la tupla (CODUSU, NRO_HOGAR, AGLOMERADO) para poder unir.

    Los tres campos se limpian de espacios y, en NRO_HOGAR y AGLOMERADO, de
    ceros a la izquierda (un archivo puede traer '02' y otro '2').

    Args:
        df: DataFrame con las columnas de config.COLS_ID_HOGAR.

    Returns:
        Copia del DataFrame con la clave normalizada.
    """
    df = df.copy()
    for columna in COLS_CLAVE:
        df[columna] = df[columna].str.strip()
    for columna in ("NRO_HOGAR", "AGLOMERADO"):
        sin_ceros = df[columna].str.lstrip("0")
        df[columna] = sin_ceros.where(sin_ceros != "", "0")
    return df


def cargar_hogares_tic(ruta):
    """Carga el archivo de hogares del módulo TIC (solo lo necesario).

    Args:
        ruta: ruta al archivo de hogares de ciencia y tecnología.

    Returns:
        DataFrame con la clave, POND_TIC y las variables de computadora e
        internet.
    """
    columnas = [*COLS_CLAVE, config.COL_POND_TIC, config.COL_TIC_COMPUTADORA,
                config.COL_TIC_INTERNET]
    return normalizar_clave(leer_columnas_hogares(ruta, columnas))


def cargar_hogares_vivienda(ruta):
    """Carga el archivo de hogares de Mercado Laboral (vivienda y PONDERA).

    Args:
        ruta: ruta al archivo de hogares de mercado laboral.

    Returns:
        DataFrame con la clave, PONDERA y las variables de vivienda de
        config.VARIABLES_VIVIENDA.
    """
    columnas = [*COLS_CLAVE, config.COL_PONDERA,
                *config.VARIABLES_VIVIENDA]
    return normalizar_clave(leer_columnas_hogares(ruta, columnas))


def clasificar_calidad_tecnologica(df):
    """Agrega la categoría de calidad tecnológica de cada hogar.

    Combina dos preguntas (computadora e internet) en las categorías de
    config.CATEGORIAS_CALIDAD_TEC. Un hogar con una respuesta distinta de
    sí/no (por ejemplo, 9 = no sabe) no se puede clasificar: queda sin
    categoría (NaN).

    Args:
        df: DataFrame con IH_II_01 (computadora) e IH_II_02 (internet).

    Returns:
        Copia de df con las columnas TIENE_PC, TIENE_INTERNET (True, False
        o NaN) y CALIDAD_TEC.
    """
    df = df.copy()
    respuestas = {config.TIC_SI: True, config.TIC_NO: False}
    df[COL_TIENE_PC] = df[config.COL_TIC_COMPUTADORA].str.strip().map(
        respuestas)
    df[COL_TIENE_INTERNET] = df[config.COL_TIC_INTERNET].str.strip().map(
        respuestas)
    df[COL_CALIDAD] = pd.Series(pd.NA, index=df.index, dtype="object")
    for (tiene_pc, tiene_internet), nombre in (
            config.CATEGORIAS_CALIDAD_TEC.items()):
        mascara = ((df[COL_TIENE_PC] == tiene_pc)
                   & (df[COL_TIENE_INTERNET] == tiene_internet))
        df.loc[mascara, COL_CALIDAD] = nombre
    return df


def cruzar_hogares(hogares_tic, hogares_vivienda):
    """Une los hogares del módulo TIC con los de Mercado Laboral.

    Usa un merge 'left' desde TIC (el análisis es sobre hogares TIC) con la
    tupla (CODUSU, NRO_HOGAR, AGLOMERADO) y validate='one_to_one' para
    detectar claves repetidas. Si hay repetidas, se conserva la primera y
    se informa. Los hogares TIC sin pareja quedan con la vivienda vacía y
    se informan.

    Args:
        hogares_tic: resultado de cargar_hogares_tic.
        hogares_vivienda: resultado de cargar_hogares_vivienda.

    Returns:
        Tupla (cruce, diagnostico). El diagnóstico es un diccionario con
        hogares_tic, hogares_vivienda, claves_repetidas_tic,
        claves_repetidas_vivienda, con_pareja, sin_pareja_en_vivienda y
        solo_en_vivienda.
    """
    repetidas_tic = int(hogares_tic.duplicated(COLS_CLAVE).sum())
    repetidas_viv = int(hogares_vivienda.duplicated(COLS_CLAVE).sum())
    tic = hogares_tic.drop_duplicates(COLS_CLAVE)
    viv = hogares_vivienda.drop_duplicates(COLS_CLAVE)
    cruce = tic.merge(viv, on=COLS_CLAVE, how="left", validate="one_to_one",
                      indicator=True)
    con_pareja = int((cruce["_merge"] == "both").sum())
    solo_viv = len(viv.merge(tic[COLS_CLAVE], on=COLS_CLAVE, how="left",
                             indicator=True).query("_merge == 'left_only'"))
    diagnostico = {
        "hogares_tic": len(hogares_tic),
        "hogares_vivienda": len(hogares_vivienda),
        "claves_repetidas_tic": repetidas_tic,
        "claves_repetidas_vivienda": repetidas_viv,
        "con_pareja": con_pareja,
        "sin_pareja_en_vivienda": len(cruce) - con_pareja,
        "solo_en_vivienda": solo_viv,
    }
    return cruce.drop(columns="_merge"), diagnostico


def agregar_region(df):
    """Agrega el código de región, obtenido del aglomerado.

    Args:
        df: DataFrame con la columna AGLOMERADO (sin ceros a la izquierda).

    Returns:
        Copia con la columna REGION_COD (NaN si el aglomerado no está en
        config.REGION_DE_AGLOMERADO).
    """
    df = df.copy()
    df[COL_REGION] = df[config.COL_AGLOMERADO].map(
        config.REGION_DE_AGLOMERADO)
    return df


def anios_disponibles_cruce(archivos):
    """Detecta los años en que se puede hacer el cruce.

    Un año sirve si existen el hogar TIC de ese año y el hogar de Mercado
    Laboral del trimestre config.TRIMESTRE_CRUCE_TIC.

    Args:
        archivos: lista devuelta por data_loader.escanear_datos.

    Returns:
        Lista de años como texto, ordenada.
    """
    tic = {a["anio"] for a in data_loader.filtrar_archivos(
        archivos, tipo=config.TIPO_HOGAR,
        categoria=config.CAT_CIENCIA_TECNOLOGIA)}
    laboral = {a["anio"] for a in data_loader.filtrar_archivos(
        archivos, tipo=config.TIPO_HOGAR,
        categoria=config.CAT_MERCADO_LABORAL,
        trimestres=[config.TRIMESTRE_CRUCE_TIC])}
    return sorted(tic & laboral)


def cargar_hogares_del_anio(anio, archivos=None):
    """Carga los dos archivos de hogares de un año, antes de cruzarlos.

    Args:
        anio: año como texto.
        archivos: lista de data_loader.escanear_datos (si es None se
            escanea la carpeta de datos).

    Returns:
        Tupla (hogares_tic, hogares_vivienda).

    Raises:
        FileNotFoundError: si falta alguno de los dos archivos del año.
    """
    if archivos is None:
        archivos = data_loader.escanear_datos()
    tic = data_loader.filtrar_archivos(
        archivos, tipo=config.TIPO_HOGAR,
        categoria=config.CAT_CIENCIA_TECNOLOGIA, anios=[anio])
    laboral = data_loader.filtrar_archivos(
        archivos, tipo=config.TIPO_HOGAR,
        categoria=config.CAT_MERCADO_LABORAL, anios=[anio],
        trimestres=[config.TRIMESTRE_CRUCE_TIC])
    if not tic or not laboral:
        raise FileNotFoundError(
            f"Para {anio} hacen falta el hogar TIC y el hogar de Mercado "
            f"Laboral {config.TRIMESTRE_CRUCE_TIC}.")
    return (cargar_hogares_tic(tic[0]["ruta"]),
            cargar_hogares_vivienda(laboral[0]["ruta"]))


def armar_base_cruce(anio, archivos=None):
    """Arma la base de hogares lista para analizar un año.

    Carga los dos archivos, los cruza, clasifica la calidad tecnológica y
    agrega la región.

    Args:
        anio: año como texto.
        archivos: lista de data_loader.escanear_datos (si es None se
            escanea la carpeta de datos).

    Returns:
        Tupla (base, diagnostico). El diagnóstico es el de cruzar_hogares
        más hogares_sin_clasificar (sin respuesta válida de computadora o
        internet).

    Raises:
        FileNotFoundError: si falta alguno de los dos archivos del año.
    """
    hogares_tic, hogares_vivienda = cargar_hogares_del_anio(anio, archivos)
    cruce, diagnostico = cruzar_hogares(hogares_tic, hogares_vivienda)
    base = agregar_region(clasificar_calidad_tecnologica(cruce))
    diagnostico["hogares_sin_clasificar"] = int(base[COL_CALIDAD].isna().sum())
    return base, diagnostico


def filtrar_region(base, region_cod):
    """Deja los hogares de una región.

    Args:
        base: resultado de armar_base_cruce.
        region_cod: código de región (clave de config.NOMBRES_REGIONES) o
            None para no filtrar.

    Returns:
        DataFrame filtrado.
    """
    if region_cod is None:
        return base
    return base[base[COL_REGION] == region_cod]


def _preparar_pesos(base, col_peso):
    """Deja los hogares clasificados y con peso válido.

    Args:
        base: base de hogares.
        col_peso: columna de peso (POND_TIC o PONDERA).

    Returns:
        Tupla (hogares, descartados): los hogares con categoría y peso
        mayor que cero (con la columna PESO numérica) y la cantidad de
        hogares que se dejaron afuera.
    """
    if col_peso not in config.COLS_PESO_CRUCE:
        raise ValueError(f"col_peso debe ser uno de {config.COLS_PESO_CRUCE}")
    hogares = base.copy()
    hogares[COL_PESO] = pd.to_numeric(hogares[col_peso], errors="coerce")
    validos = hogares[COL_CALIDAD].notna() & (hogares[COL_PESO] > 0)
    return hogares[validos], int((~validos).sum())


def etiquetar_vivienda(serie, variable):
    """Traduce los códigos de una variable de vivienda a su nombre.

    Args:
        serie: columna con los códigos (texto).
        variable: código de la variable (clave de config.VARIABLES_VIVIENDA).

    Returns:
        Serie con los nombres. Vacío o NaN -> 'Sin dato'; un código que no
        está en config.ETIQUETAS_VIVIENDA -> 'Código X'.
    """
    nombres = config.ETIQUETAS_VIVIENDA.get(variable, {})
    codigos = serie.fillna("").str.strip()
    etiquetas = codigos.map(nombres)
    desconocido = etiquetas.isna() & (codigos != "")
    etiquetas = etiquetas.where(~desconocido, "Código " + codigos)
    return etiquetas.fillna(config.ETIQUETA_SIN_DATO_VIVIENDA)


def _orden_grupos(variable, presentes):
    """Ordena los grupos de vivienda como figuran en config (y al final los
    desconocidos)."""
    conocidos = list(config.ETIQUETAS_VIVIENDA.get(variable, {}).values())
    primero = [g for g in conocidos if g in presentes]
    resto = sorted(g for g in presentes if g not in primero)
    return primero + resto


def porcentaje_por_vivienda(base, variable,
                            col_peso=config.COLS_PESO_CRUCE[0]):
    """Calcula el % de hogares de cada calidad tecnológica por vivienda.

    Estructura elegida: groupby + agg (muestra y suma de pesos) + unstack para
    pasar la calidad tecnológica a columnas. El porcentaje de cada fila se
    calcula sobre el total ponderado de ese grupo de vivienda, así cada barra
    del gráfico suma 100.

    Args:
        base: resultado de armar_base_cruce (ya filtrado por región, si
            corresponde).
        variable: variable de vivienda (clave de config.VARIABLES_VIVIENDA).
        col_peso: columna de peso: POND_TIC (por defecto) o PONDERA.

    Returns:
        DataFrame largo con las columnas COL_GRUPO, COL_CATEGORIA,
        COL_MUESTRA, COL_EXPANDIDOS y COL_PORCENTAJE (una fila por grupo y
        categoría, incluso con 0 hogares). Vacío si no hay hogares válidos.
    """
    hogares, _ = _preparar_pesos(base, col_peso)
    if hogares.empty:
        return pd.DataFrame(columns=[COL_GRUPO, COL_CATEGORIA, COL_MUESTRA,
                                     COL_EXPANDIDOS, COL_PORCENTAJE])
    hogares[COL_GRUPO] = etiquetar_vivienda(hogares[variable], variable)
    categorias = list(config.CATEGORIAS_CALIDAD_TEC.values())
    resumen = hogares.groupby([COL_GRUPO, COL_CALIDAD]).agg(
        muestra=(COL_PESO, "size"), ponderados=(COL_PESO, "sum"))
    ponderados = resumen["ponderados"].unstack(fill_value=0).reindex(
        columns=categorias, fill_value=0)
    muestra = resumen["muestra"].unstack(fill_value=0).reindex(
        columns=categorias, fill_value=0)
    porcentajes = ponderados.div(ponderados.sum(axis=1), axis=0) * 100
    orden = _orden_grupos(variable, porcentajes.index)
    largo = pd.concat({
        COL_MUESTRA: muestra, COL_EXPANDIDOS: ponderados.round(),
        COL_PORCENTAJE: porcentajes.round(2),
    }, axis=1).reindex(orden)
    largo = largo.stack(level=1, future_stack=True)
    largo.index.names = [COL_GRUPO, COL_CATEGORIA]
    largo = largo.reset_index()
    largo[COL_MUESTRA] = largo[COL_MUESTRA].astype(int)
    largo[COL_EXPANDIDOS] = largo[COL_EXPANDIDOS].astype(int)
    return largo


def porcentaje_por_vivienda_pivot(base, variable,
                                  col_peso=config.COLS_PESO_CRUCE[0]):
    """Mismo cálculo que porcentaje_por_vivienda, pero con pivot_table.

    Existe para comparar las dos estrategias en la hoja de ayuda: da los
    mismos porcentajes que groupby + unstack, en menos líneas pero sin
    controlar tan fácil las categorías sin hogares.

    Args:
        base: base de hogares.
        variable: variable de vivienda.
        col_peso: columna de peso.

    Returns:
        DataFrame ancho: una fila por grupo de vivienda y una columna por
        categoría de calidad tecnológica, con el % de hogares.
    """
    hogares, _ = _preparar_pesos(base, col_peso)
    hogares[COL_GRUPO] = etiquetar_vivienda(hogares[variable], variable)
    categorias = list(config.CATEGORIAS_CALIDAD_TEC.values())
    ancho = hogares.pivot_table(index=COL_GRUPO, columns=COL_CALIDAD,
                                values=COL_PESO, aggfunc="sum", fill_value=0)
    ancho = ancho.reindex(columns=categorias, fill_value=0)
    return (ancho.div(ancho.sum(axis=1), axis=0) * 100).round(2)


def grupos_de_vivienda(base, variable):
    """Lista los grupos de una variable de vivienda presentes en la base.

    Sirve para armar el filtro del mapa (por ejemplo, 'Casa' y
    'Departamento' para el tipo de vivienda).

    Args:
        base: resultado de armar_base_cruce.
        variable: variable de vivienda (clave de config.VARIABLES_VIVIENDA).

    Returns:
        Lista de nombres de grupo, en el orden de config.
    """
    presentes = set(etiquetar_vivienda(base[variable], variable))
    return _orden_grupos(variable, presentes)


def acceso_por_aglomerado(base, col_peso=config.COLS_PESO_CRUCE[0],
                          variable=None, grupo=None):
    """Calcula el % de hogares de cada calidad tecnológica por aglomerado.

    Es la tabla que necesita el mapa del bloque D. Si se indica una variable
    de vivienda y uno de sus grupos, se calcula solo sobre los hogares de ese
    grupo (por ejemplo, solo las casas).

    Args:
        base: resultado de armar_base_cruce.
        col_peso: columna de peso.
        variable: variable de vivienda para filtrar (None = sin filtro).
        grupo: nombre del grupo a conservar (None = sin filtro).

    Returns:
        DataFrame con una fila por aglomerado: Código, Nombre, hogares de
        muestra y un % por cada categoría de calidad tecnológica.
    """
    hogares, _ = _preparar_pesos(base, col_peso)
    if variable is not None and grupo is not None:
        etiquetas = etiquetar_vivienda(hogares[variable], variable)
        hogares = hogares[etiquetas == grupo]
    categorias = list(config.CATEGORIAS_CALIDAD_TEC.values())
    por_aglomerado = hogares.groupby(
        [config.COL_AGLOMERADO, COL_CALIDAD])[COL_PESO].sum()
    ancho = por_aglomerado.unstack(fill_value=0).reindex(
        columns=categorias, fill_value=0)
    porcentajes = (ancho.div(ancho.sum(axis=1), axis=0) * 100).round(2)
    porcentajes.insert(0, "Hogares (muestra)",
                       hogares.groupby(config.COL_AGLOMERADO).size())
    porcentajes.insert(0, "Nombre", porcentajes.index.map(
        lambda c: config.AGLOMERADOS.get(c, c)))
    porcentajes.index.name = "Código"
    return porcentajes.reset_index()


def resumir_total(base, col_peso=config.COLS_PESO_CRUCE[0]):
    """Calcula la distribución de calidad tecnológica del conjunto de hogares.

    Args:
        base: base de hogares (ya filtrada).
        col_peso: columna de peso.

    Returns:
        Serie con el % de hogares de cada categoría (índice: categorías en
        el orden de config). Vacía si no hay hogares válidos.
    """
    hogares, _ = _preparar_pesos(base, col_peso)
    if hogares.empty:
        return pd.Series(dtype=float)
    categorias = list(config.CATEGORIAS_CALIDAD_TEC.values())
    pesos = hogares.groupby(COL_CALIDAD)[COL_PESO].sum().reindex(
        categorias, fill_value=0)
    return pesos / pesos.sum() * 100


def describir_resultados(tabla, total, anio, ambito, variable, col_peso,
                         descartados=0):
    """Escribe, en texto, qué muestran los resultados elegidos.

    El texto se arma con los datos: cambia con el año, la región y la variable
    de vivienda seleccionados.

    Args:
        tabla: resultado de porcentaje_por_vivienda.
        total: resultado de resumir_total (misma selección).
        anio: año elegido.
        ambito: nombre de la región elegida (o 'Todas las regiones').
        variable: variable de vivienda elegida.
        col_peso: peso usado.
        descartados: hogares dejados afuera por no tener datos válidos.

    Returns:
        Texto en markdown (un párrafo por idea). Si no hay datos, un aviso.
    """
    if tabla.empty or total.empty:
        return "No hay hogares con datos válidos para esta selección."
    mejor_cat = config.CATEGORIAS_CALIDAD_TEC[(True, True)]
    peor_cat = config.CATEGORIAS_CALIDAD_TEC[(False, False)]
    nombre_var = config.VARIABLES_VIVIENDA[variable].lower()
    parrafos = [
        f"En **{ambito}** ({anio}), el **{total[mejor_cat]:.1f}%** de los "
        f"hogares tiene {mejor_cat.lower()}, y el **{total[peor_cat]:.1f}%** "
        f"no tiene ninguno de los dos."
    ]
    muestra_grupo = tabla.groupby(COL_GRUPO)[COL_MUESTRA].sum()
    con_todo = tabla[tabla[COL_CATEGORIA] == mejor_cat]
    confiables = con_todo[con_todo[COL_GRUPO].map(muestra_grupo)
                          >= config.MIN_MUESTRA_GRUPO]
    if len(confiables) >= 2:
        arriba = confiables.loc[confiables[COL_PORCENTAJE].idxmax()]
        abajo = confiables.loc[confiables[COL_PORCENTAJE].idxmin()]
        brecha = arriba[COL_PORCENTAJE] - abajo[COL_PORCENTAJE]
        parrafos.append(
            f"Según {nombre_var}, el mayor acceso a {mejor_cat.lower()} está "
            f"en **{arriba[COL_GRUPO]}** ({arriba[COL_PORCENTAJE]:.1f}%) y el "
            f"menor en **{abajo[COL_GRUPO]}** ({abajo[COL_PORCENTAJE]:.1f}%): "
            f"una brecha de {brecha:.1f} puntos porcentuales.")
    chicos = muestra_grupo[muestra_grupo < config.MIN_MUESTRA_GRUPO]
    if len(chicos):
        parrafos.append(
            "Cuidado: " + ", ".join(f"{g} ({n} hogares)"
                                    for g, n in chicos.items())
            + f" tienen menos de {config.MIN_MUESTRA_GRUPO} hogares en la "
            "muestra, por lo que sus porcentajes son poco confiables y no "
            "se usaron para la comparación.")
    parrafos.append(
        f"Los porcentajes están ponderados con `{col_peso}`"
        + (f"; se dejaron afuera {descartados} hogares sin respuesta válida "
           "de computadora o internet." if descartados else "."))
    return "\n\n".join(parrafos)


def contar_descartados(base, col_peso=config.COLS_PESO_CRUCE[0]):
    """Cuenta los hogares que no entran en el análisis.

    Args:
        base: base de hogares (ya filtrada).
        col_peso: columna de peso.

    Returns:
        Cantidad de hogares sin categoría de calidad tecnológica o sin peso
        válido.
    """
    return _preparar_pesos(base, col_peso)[1]


def a_csv(tabla):
    """Convierte una tabla a CSV listo para descargar y abrir en Excel.

    Args:
        tabla: DataFrame a exportar.

    Returns:
        Bytes en utf-8 con BOM (para que Excel respete las tildes).
    """
    return tabla.to_csv(index=False).encode("utf-8-sig")