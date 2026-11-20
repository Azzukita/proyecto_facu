"""Bloque B: procesamiento de Mercado Laboral y género con pandas.

Acá está la lógica de cálculo. La página de Streamlit (P3) solo llama a
estas funciones y muestra los resultados.
"""
import pandas as pd

from src import config, data_loader

# Columnas que se leen de los archivos de individuos. ANO4 y TRIMESTRE
# identifican el período; AGLOMERADO, ESTADO y CH04 (sexo) son las
# dimensiones del análisis; PONDERA es el factor de expansión.
COLUMNAS_B = list(config.COLS_PERIODO) + [
    config.COL_AGLOMERADO,
    config.COL_ESTADO,
    config.COL_SEXO,
    config.COL_PONDERA,
]


def _leer_individuos(ruta, columnas):
    """Lee un archivo de individuos con pandas, solo con las columnas dadas.

    Prueba primero config.ENCODING y, si el archivo no se puede decodificar,
    las codificaciones de config.ENCODINGS_ALTERNATIVOS.

    Args:
        ruta: ruta al archivo.
        columnas: nombres de las columnas a leer.

    Returns:
        DataFrame con todas las columnas leídas como texto.
    """
    encodings = (config.ENCODING,) + tuple(config.ENCODINGS_ALTERNATIVOS)
    for encoding in encodings:
        try:
            return pd.read_csv(
                ruta,
                sep=config.SEPARADOR,
                usecols=columnas,
                dtype=str,
                encoding=encoding,
            )
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(
        "utf-8", b"", 0, 1, f"No se pudo decodificar el archivo: {ruta}")


def cargar_datos_individuos(anios=None, directorio=None, columnas=None):
    """Carga y consolida los archivos de individuos de Mercado Laboral.

    Busca los archivos con data_loader.buscar_archivos (no hay rutas fijas),
    lee solo las columnas necesarias y los une en un único DataFrame.

    Args:
        anios: lista de años como texto, por ejemplo ['2023', '2024']
            (None = todos los que haya en la carpeta de datos).
        directorio: carpeta raíz de los datos (por defecto
            config.DIR_DATOS).
        columnas: columnas a leer (por defecto COLUMNAS_B).

    Returns:
        DataFrame con una fila por persona. ANO4 y TRIMESTRE son enteros,
        PONDERA es numérico (NaN si no se puede convertir) y el resto de
        las columnas queda como texto. Si no hay archivos, un DataFrame
        vacío con las columnas pedidas.
    """
    columnas = list(columnas or COLUMNAS_B)
    archivos = data_loader.buscar_archivos(
        tipo=config.TIPO_INDIVIDUO,
        categoria=config.CAT_MERCADO_LABORAL,
        anios=anios,
        directorio=directorio,
    )
    if not archivos:
        return pd.DataFrame(columns=columnas)

    tablas = [_leer_individuos(a["ruta"], columnas) for a in archivos]
    datos = pd.concat(tablas, ignore_index=True)

    for columna in config.COLS_PERIODO:
        datos[columna] = pd.to_numeric(datos[columna], errors="coerce")
    datos = datos.dropna(subset=list(config.COLS_PERIODO))
    for columna in config.COLS_PERIODO:
        datos[columna] = datos[columna].astype(int)
    datos[config.COL_PONDERA] = pd.to_numeric(
        datos[config.COL_PONDERA].str.replace(",", ".", regex=False),
        errors="coerce",
    )
    for columna in (config.COL_AGLOMERADO, config.COL_ESTADO,
                    config.COL_SEXO):
        datos[columna] = datos[columna].str.strip()
    return datos


def anios_disponibles(datos):
    """Devuelve los años que tiene el DataFrame, de menor a mayor.

    Sirve para armar las opciones del filtro de años sin escribirlas a mano.

    Args:
        datos: DataFrame devuelto por cargar_datos_individuos.

    Returns:
        Lista de años (enteros) sin repetir.
    """
    return sorted(datos["ANO4"].unique().tolist())


def aglomerados_disponibles(datos):
    """Devuelve los códigos de aglomerado que tiene el DataFrame.

    Args:
        datos: DataFrame devuelto por cargar_datos_individuos.

    Returns:
        Lista de códigos (texto) sin repetir, ordenados como número.
    """
    codigos = datos[config.COL_AGLOMERADO].dropna().unique().tolist()
    return sorted(codigos, key=int)


def validar_rango_anios(datos, anio_desde, anio_hasta, minimo=None):
    """Verifica que el rango de años sea válido para el análisis.

    El rango es válido si el desde no es mayor que el hasta y si contiene,
    como mínimo, config.MIN_ANIOS_B años con datos. Se cuentan los años
    que realmente hay en el DataFrame, no los números del rango.

    Args:
        datos: DataFrame devuelto por cargar_datos_individuos.
        anio_desde: primer año del rango (incluido).
        anio_hasta: último año del rango (incluido).
        minimo: años con datos que debe tener el rango (por defecto
            config.MIN_ANIOS_B).

    Raises:
        ValueError: si el rango está invertido o tiene menos años con
            datos que el mínimo.
    """
    if minimo is None:
        minimo = config.MIN_ANIOS_B
    if anio_desde > anio_hasta:
        raise ValueError("El año inicial no puede ser mayor que el final.")
    en_rango = [a for a in anios_disponibles(datos)
                if anio_desde <= a <= anio_hasta]
    if len(en_rango) < minimo:
        raise ValueError(
            f"El rango tiene {len(en_rango)} año(s) con datos y se "
            f"necesitan al menos {minimo}.")


def filtrar_mercado_laboral(datos, anio_desde=None, anio_hasta=None,
                            aglomerados=None, trimestres=None):
    """Filtra el DataFrame por rango de años, aglomerados y trimestres.

    Cada filtro es opcional: si es None no se aplica. Solo filtra; no
    calcula nada ni descarta estados.

    Args:
        datos: DataFrame devuelto por cargar_datos_individuos.
        anio_desde: primer año (incluido).
        anio_hasta: último año (incluido).
        aglomerados: lista de códigos de aglomerado como texto.
        trimestres: lista de trimestres como entero, por ejemplo [1] para
            comparar el mismo trimestre en varios años.

    Returns:
        Un DataFrame nuevo con las filas que cumplen todos los filtros.
    """
    mascara = pd.Series(True, index=datos.index)
    if anio_desde is not None:
        mascara &= datos["ANO4"] >= anio_desde
    if anio_hasta is not None:
        mascara &= datos["ANO4"] <= anio_hasta
    if aglomerados is not None:
        codigos = [str(c).strip() for c in aglomerados]
        mascara &= datos[config.COL_AGLOMERADO].isin(codigos)
    if trimestres is not None:
        mascara &= datos["TRIMESTRE"].isin(list(trimestres))
    return datos[mascara].copy()


# Este es el grupo de columnas que se usa por defecto para los cálculos
GRUPO_TRIMESTRAL = ["ANO4", "TRIMESTRE", config.COL_AGLOMERADO]


def contar_poblacion_por_estado(datos, agrupar_por=None):
    """Suma PONDERA de ocupados, desocupados e inactivos por grupo.

    Solo se tienen en cuenta los estados de config.ESTADOS_DISTRIBUCION
    (ocupado, desocupado e inactivo): quedan afuera ESTADO = 0 (entrevista
    no realizada) y ESTADO = 4 (menores de 10 años).

    Primero se suma por trimestre. Si 'agrupar_por' no incluye TRIMESTRE
    (por ejemplo, un resultado anual), después se promedian los
    trimestres: cada trimestre ya representa a toda la población, así que
    sumarlos contaría a cada persona varias veces.

    Args:
        datos: DataFrame devuelto por cargar_datos_individuos (o filtrado).
        agrupar_por: lista de columnas por las que se agrupa (por defecto
            GRUPO_TRIMESTRAL). Se pueden agregar otras, como CH04.

    Returns:
        DataFrame con las columnas de agrupación y una columna por estado
        (ocupados, desocupados, inactivos) con la población ponderada.
        Un estado sin casos en un grupo queda en 0.
    """
    agrupar_por = list(agrupar_por or GRUPO_TRIMESTRAL)
    nombres = [config.NOMBRES_ESTADO[e] for e in config.ESTADOS_DISTRIBUCION]
    base = datos[datos[config.COL_ESTADO].isin(config.ESTADOS_DISTRIBUCION)]
    if base.empty:
        return pd.DataFrame(columns=agrupar_por + nombres)

    # Nivel más fino: el trimestre, que siempre se incluye.
    niveles = agrupar_por + [c for c in ("ANO4", "TRIMESTRE")
                             if c not in agrupar_por]
    tabla = (base.groupby(niveles + [config.COL_ESTADO])[config.COL_PONDERA]
             .sum()
             .unstack(fill_value=0)
             .reindex(columns=list(config.ESTADOS_DISTRIBUCION),
                      fill_value=0))
    if niveles != agrupar_por:
        tabla = tabla.groupby(level=agrupar_por).mean()
    tabla.columns = nombres
    return tabla.reset_index()


def calcular_distribucion_estado(datos, agrupar_por=None):
    """Calcula la distribución de la población entre los tres estados.

    Args:
        datos: DataFrame devuelto por cargar_datos_individuos (o filtrado).
        agrupar_por: columnas de agrupación (ver contar_poblacion_por_estado).

    Returns:
        DataFrame con las columnas de agrupación, ocupados, desocupados,
        inactivos, poblacion (la suma de los tres) y el porcentaje de cada
        estado sobre la población (pct_ocupados, pct_desocupados,
        pct_inactivos). El porcentaje es NaN si la población es 0.
    """
    tabla = contar_poblacion_por_estado(datos, agrupar_por)
    nombres = [config.NOMBRES_ESTADO[e] for e in config.ESTADOS_DISTRIBUCION]
    tabla["poblacion"] = tabla[nombres].sum(axis=1)
    for nombre in nombres:
        tabla["pct_" + nombre] = (
            100 * tabla[nombre] / tabla["poblacion"].where(
                tabla["poblacion"] > 0))
    return tabla


def calcular_tasa_desempleo(datos, agrupar_por=None):
    """Calcula la tasa de desempleo ponderada por grupo.

    PEA = ocupados + desocupados (ponderados con PONDERA).
    Tasa de desempleo = desocupados / PEA * 100.

    Args:
        datos: DataFrame devuelto por cargar_datos_individuos (o filtrado).
        agrupar_por: columnas de agrupación (ver contar_poblacion_por_estado).

    Returns:
        DataFrame con las columnas de agrupación, ocupados, desocupados,
        pea y tasa_desempleo. La tasa es NaN si la PEA es 0.
    """
    agrupar_por = list(agrupar_por or GRUPO_TRIMESTRAL)
    tabla = contar_poblacion_por_estado(datos, agrupar_por)
    ocupados = config.NOMBRES_ESTADO[config.ESTADO_OCUPADO]
    desocupados = config.NOMBRES_ESTADO[config.ESTADO_DESOCUPADO]
    tabla["pea"] = tabla[[config.NOMBRES_ESTADO[e]
                          for e in config.ESTADOS_ACTIVOS]].sum(axis=1)
    tabla["tasa_desempleo"] = (
        100 * tabla[desocupados] / tabla["pea"].where(tabla["pea"] > 0))
    return tabla[agrupar_por + [ocupados, desocupados, "pea",
                                "tasa_desempleo"]]


# =============================================================================
# INDICADORES POR SEXO Y BRECHAS DE GÉNERO
# =============================================================================
# Sufijo que lleva cada sexo en los nombres de columna (sin tildes).

SUFIJO_SEXO = {
    config.NOMBRES_SEXO[config.SEXO_VARON]: "varon",
    config.NOMBRES_SEXO[config.SEXO_MUJER]: "mujer",
}
# Indicadores sobre los que se calcula la brecha de género.
METRICAS_BRECHA = ["tasa_desempleo", "pct_ocupados", "pct_inactivos"]
# Nombre que se usa para el total de ambos sexos en la columna 'sexo'
TOTAL_SEXO = "Total"


def _indicadores(datos, agrupar_por):
    """Junta distribución y tasa de desempleo en una sola tabla.

    Args:
        datos: DataFrame devuelto por cargar_datos_individuos (o filtrado).
        agrupar_por: lista de columnas de agrupación.

    Returns:
        DataFrame con las columnas de agrupación, ocupados, desocupados,
        inactivos, poblacion, pct_ocupados, pct_desocupados, pct_inactivos,
        pea y tasa_desempleo.
    """
    distribucion = calcular_distribucion_estado(datos, agrupar_por)
    tasa = calcular_tasa_desempleo(datos, agrupar_por)
    return distribucion.merge(
        tasa[agrupar_por + ["pea", "tasa_desempleo"]],
        on=agrupar_por, how="left")


def calcular_indicadores_genero(datos, agrupar_por=None):
    """Calcula tasa de desempleo y distribución por sexo (CH04).

    Args:
        datos: DataFrame devuelto por cargar_datos_individuos (o filtrado).
        agrupar_por: columnas de agrupación sin incluir el sexo (por
            defecto GRUPO_TRIMESTRAL). El sexo se agrega solo.

    Returns:
        DataFrame en formato largo: una fila por grupo y sexo. Las
        columnas son las de agrupación, 'sexo' (Varón o Mujer) y los
        indicadores de _indicadores.
    """
    agrupar_por = list(agrupar_por or GRUPO_TRIMESTRAL)
    tabla = _indicadores(datos, agrupar_por + [config.COL_SEXO])
    codigos = tabla[config.COL_SEXO]
    tabla["sexo"] = codigos.map(config.NOMBRES_SEXO).fillna(codigos)
    resto = [c for c in tabla.columns
             if c not in agrupar_por + [config.COL_SEXO, "sexo"]]
    return tabla[agrupar_por + ["sexo"] + resto]


def calcular_brechas_genero(indicadores, agrupar_por=None, metricas=None):
    """Calcula la brecha de género de cada indicador.

    Brecha = valor de las mujeres - valor de los varones, en puntos
    porcentuales. Un valor positivo significa que el indicador es mayor
    para las mujeres.

    Args:
        indicadores: resultado de calcular_indicadores_genero.
        agrupar_por: las mismas columnas de agrupación con que se calculó
            (por defecto GRUPO_TRIMESTRAL).
        metricas: indicadores a comparar (por defecto METRICAS_BRECHA).

    Returns:
        DataFrame con una fila por grupo y, por cada indicador, las
        columnas '<indicador>_varon', '<indicador>_mujer' y
        'brecha_<indicador>'. Si falta un sexo en un grupo, la brecha es
        NaN.
    """
    agrupar_por = list(agrupar_por or GRUPO_TRIMESTRAL)
    metricas = list(metricas or METRICAS_BRECHA)
    ancho = indicadores.pivot_table(
        index=agrupar_por, columns="sexo", values=metricas)
    ancho.columns = [f"{metrica}_{SUFIJO_SEXO.get(sexo, sexo)}"
                     for metrica, sexo in ancho.columns]
    for metrica in metricas:
        for sufijo in SUFIJO_SEXO.values():
            columna = f"{metrica}_{sufijo}"
            if columna not in ancho.columns:
                ancho[columna] = float("nan")
        ancho["brecha_" + metrica] = (
            ancho[f"{metrica}_mujer"] - ancho[f"{metrica}_varon"])
    columnas = [f"{m}_{s}" for m in metricas
                for s in ("varon", "mujer")] + [
        "brecha_" + m for m in metricas]
    return ancho[columnas].reset_index()


# =============================================================================
# PASO 5: DATOS LISTOS PARA GRAFICAR Y PARA EL BLOQUE D (MAPAS)
# =============================================================================
# Cómo se agrupa cada período. Para agregar uno nuevo (por ejemplo,
# semestral) habría que sumar una entrada acá y su etiqueta.
GRUPOS_POR_PERIODO = {
    "trimestral": GRUPO_TRIMESTRAL,
    "anual": ["ANO4", config.COL_AGLOMERADO],
}


def _grupo_del_periodo(periodo):
    """Devuelve las columnas de agrupación de un tipo de período.

    Args:
        periodo: 'trimestral' o 'anual' (claves de GRUPOS_POR_PERIODO).

    Returns:
        Lista de columnas de agrupación.

    Raises:
        ValueError: si el período no existe.
    """
    if periodo not in GRUPOS_POR_PERIODO:
        raise ValueError(
            f"Período desconocido: {periodo!r}. Opciones: "
            f"{list(GRUPOS_POR_PERIODO)}")
    return list(GRUPOS_POR_PERIODO[periodo])


def _etiqueta_periodo(tabla, periodo):
    """Arma la etiqueta de período de cada fila.

    Args:
        tabla: DataFrame con ANO4 y, si es trimestral, TRIMESTRE.
        periodo: 'trimestral' o 'anual'.

    Returns:
        Serie de texto, por ejemplo '2024-T1' (trimestral) o '2024'
        (anual).
    """
    etiqueta = tabla["ANO4"].astype(str)
    if periodo == "trimestral":
        etiqueta = etiqueta + "-T" + tabla["TRIMESTRE"].astype(str)
    return etiqueta


def _agregar_etiquetas(tabla, periodo):
    """Agrega el nombre del aglomerado y la etiqueta del período.

    Args:
        tabla: DataFrame con ANO4, AGLOMERADO y, si es trimestral,
            TRIMESTRE.
        periodo: 'trimestral' o 'anual'.

    Returns:
        La misma tabla con las columnas 'aglomerado_nombre' y 'periodo'
        (por ejemplo '2024-T1' o '2024'), ordenada por período, aglomerado
        y sexo (si lo tiene).
    """
    codigos = tabla[config.COL_AGLOMERADO]
    tabla["aglomerado_nombre"] = codigos.map(config.AGLOMERADOS).fillna(
        codigos)
    tabla["periodo"] = _etiqueta_periodo(tabla, periodo)
    orden = ["ANO4"]
    if periodo == "trimestral":
        orden.append("TRIMESTRE")
    orden.append("aglomerado_nombre")
    if "sexo" in tabla.columns:
        orden.append("sexo")
    return tabla.sort_values(orden).reset_index(drop=True)


def preparar_datos_evolucion(datos, anio_desde, anio_hasta,
                             aglomerados=None, periodo="trimestral",
                             trimestres=None):
    """Prepara la tabla para graficar la evolución y las brechas.

    Valida el rango de años, filtra y calcula los indicadores del total y
    de cada sexo.

    Args:
        datos: DataFrame devuelto por cargar_datos_individuos.
        anio_desde: primer año (incluido).
        anio_hasta: último año (incluido).
        aglomerados: lista de códigos de aglomerado (None = todos).
        periodo: 'trimestral' o 'anual'.
        trimestres: lista de trimestres a incluir (None = todos). Permite
            comparar el mismo trimestre en varios años.

    Returns:
        DataFrame en formato largo con una fila por período, aglomerado y
        sexo ('Total', 'Varón' o 'Mujer'). Incluye las columnas de
        agrupación, 'periodo', 'aglomerado_nombre', 'sexo' y los
        indicadores (ocupados, desocupados, inactivos, poblacion, pct_*,
        pea y tasa_desempleo).

    Raises:
        ValueError: si el rango de años no es válido o el período no
            existe.
    """
    validar_rango_anios(datos, anio_desde, anio_hasta)
    agrupar_por = _grupo_del_periodo(periodo)
    filtrados = filtrar_mercado_laboral(
        datos, anio_desde, anio_hasta, aglomerados, trimestres)
    total = _indicadores(filtrados, agrupar_por)
    total["sexo"] = TOTAL_SEXO
    por_sexo = calcular_indicadores_genero(filtrados, agrupar_por)
    tabla = pd.concat([total, por_sexo], ignore_index=True)
    return _agregar_etiquetas(tabla, periodo)


def preparar_datos_mapa(datos, periodo="trimestral"):
    """Prepara la tabla para el Bloque D (mapas).

    Una fila por período y aglomerado, con los indicadores del total y los
    desagregados por sexo. No filtra: recibe los datos que se quieran
    mapear.

    Args:
        datos: DataFrame devuelto por cargar_datos_individuos (o filtrado).
        periodo: 'trimestral' o 'anual'.

    Returns:
        DataFrame con ANO4, TRIMESTRE (solo si es trimestral), AGLOMERADO,
        ocupados, desocupados, inactivos, poblacion, pct_*, pea,
        tasa_desempleo, las columnas por sexo y las brechas (ver
        calcular_brechas_genero), más 'aglomerado_nombre' y 'periodo'.
    """
    agrupar_por = _grupo_del_periodo(periodo)
    total = _indicadores(datos, agrupar_por)
    brechas = calcular_brechas_genero(
        calcular_indicadores_genero(datos, agrupar_por), agrupar_por)
    tabla = total.merge(brechas, on=agrupar_por, how="left")
    return _agregar_etiquetas(tabla, periodo)


# =============================================================================
# PASO 6: APOYO A LA PÁGINA P3 (resúmenes, descripción y formatos)
# =============================================================================
# Indicadores que el usuario puede elegir para graficar.
METRICAS_EVOLUCION = {
    "Tasa de desempleo (%)": "tasa_desempleo",
    "Población ocupada (% de la población)": "pct_ocupados",
    "Población inactiva (% de la población)": "pct_inactivos",
}


def formatear_numero(valor, con_signo=False):
    """Da formato a un número: dos decimales y coma decimal (7,61).

    Args:
        valor: número a formatear.
        con_signo: si es True agrega el signo + a los positivos.

    Returns:
        Texto con el número, o 's/d' si el valor no está disponible.
    """
    if valor != valor:
        return "s/d"
    formato = "+.2f" if con_signo else ".2f"
    return format(valor, formato).replace(".", ",")


def preparar_datos_distribucion(tabla, sexo=TOTAL_SEXO):
    """Pasa la distribución de la población a formato largo para graficar.

    Args:
        tabla: resultado de preparar_datos_evolucion.
        sexo: 'Total', 'Varón' o 'Mujer'.

    Returns:
        DataFrame con una fila por período, aglomerado y estado, con las
        columnas 'estado' (Ocupados, Desocupados, Inactivos) y
        'porcentaje' (% de la población).
    """
    columnas = ["pct_" + config.NOMBRES_ESTADO[e]
                for e in config.ESTADOS_DISTRIBUCION]
    identificadores = [c for c in ("ANO4", "TRIMESTRE", "AGLOMERADO",
                                   "aglomerado_nombre", "periodo")
                       if c in tabla.columns]
    largo = tabla[tabla["sexo"] == sexo].melt(
        id_vars=identificadores, value_vars=columnas,
        var_name="estado", value_name="porcentaje")
    largo["estado"] = (largo["estado"].str.replace("pct_", "", regex=False)
                       .str.capitalize())
    return largo


def preparar_datos_brechas(tabla, periodo):
    """Calcula las brechas de género a partir de la tabla de evolución.

    Args:
        tabla: resultado de preparar_datos_evolucion.
        periodo: 'trimestral' o 'anual' (el mismo con que se armó tabla).

    Returns:
        DataFrame con una fila por período y aglomerado, con las columnas
        de calcular_brechas_genero más 'aglomerado_nombre' y 'periodo'.
    """
    por_sexo = tabla[tabla["sexo"] != TOTAL_SEXO]
    brechas = calcular_brechas_genero(
        por_sexo, _grupo_del_periodo(periodo))
    return _agregar_etiquetas(brechas, periodo)


def resumir_seleccion(tabla, periodo):
    """Resume los aglomerados elegidos como si fueran un único conjunto.

    Suma la población ponderada de todos los aglomerados de la tabla
    (por período y sexo) y recalcula tasa y porcentajes sobre esa suma.

    Args:
        tabla: resultado de preparar_datos_evolucion.
        periodo: 'trimestral' o 'anual'.

    Returns:
        DataFrame con una fila por período y sexo, ordenado por período,
        con ocupados, desocupados, inactivos, poblacion, pea,
        tasa_desempleo, los pct_* y 'periodo'.
    """
    agrupar_por = [c for c in _grupo_del_periodo(periodo)
                   if c != config.COL_AGLOMERADO] + ["sexo"]
    nombres = [config.NOMBRES_ESTADO[e] for e in config.ESTADOS_DISTRIBUCION]
    resumen = tabla.groupby(agrupar_por)[nombres].sum().reset_index()
    resumen["poblacion"] = resumen[nombres].sum(axis=1)
    resumen["pea"] = resumen[[config.NOMBRES_ESTADO[e]
                              for e in config.ESTADOS_ACTIVOS]].sum(axis=1)
    desocupados = config.NOMBRES_ESTADO[config.ESTADO_DESOCUPADO]
    resumen["tasa_desempleo"] = (
        100 * resumen[desocupados] / resumen["pea"].where(resumen["pea"] > 0))
    for nombre in nombres:
        resumen["pct_" + nombre] = (
            100 * resumen[nombre] / resumen["poblacion"].where(
                resumen["poblacion"] > 0))
    resumen["periodo"] = _etiqueta_periodo(resumen, periodo)
    orden = [c for c in ("ANO4", "TRIMESTRE") if c in resumen.columns]
    return resumen.sort_values(orden + ["sexo"]).reset_index(drop=True)


def indicadores_principales(tabla, periodo):
    """Calcula los indicadores destacados del último período.

    Args:
        tabla: resultado de preparar_datos_evolucion.
        periodo: 'trimestral' o 'anual'.

    Returns:
        Diccionario con 'periodo' (el último), 'periodo_inicial',
        'tasa_total', 'tasa_varon', 'tasa_mujer' (tasas de desempleo del
        conjunto de aglomerados en el último período), 'brecha' (mujer -
        varón, en puntos porcentuales) y 'variacion_total' (cambio de la
        tasa total entre el primer y el último período). Los valores que
        no se pueden calcular son NaN.
    """
    resumen = resumir_seleccion(tabla, periodo)
    periodos = resumen["periodo"].unique().tolist()
    primero, ultimo = periodos[0], periodos[-1]

    def tasa(etiqueta, sexo):
        fila = resumen[(resumen["periodo"] == etiqueta)
                       & (resumen["sexo"] == sexo)]
        return float(fila["tasa_desempleo"].iloc[0]) if len(fila) \
            else float("nan")

    varon = config.NOMBRES_SEXO[config.SEXO_VARON]
    mujer = config.NOMBRES_SEXO[config.SEXO_MUJER]
    total_ultimo = tasa(ultimo, TOTAL_SEXO)
    return {
        "periodo": ultimo,
        "periodo_inicial": primero,
        "tasa_total": total_ultimo,
        "tasa_varon": tasa(ultimo, varon),
        "tasa_mujer": tasa(ultimo, mujer),
        "brecha": tasa(ultimo, mujer) - tasa(ultimo, varon),
        "variacion_total": total_ultimo - tasa(primero, TOTAL_SEXO),
    }


def generar_descripcion(tabla, periodo, umbral_estable=0.05):
    """Redacta la descripción de los resultados según la selección.

    El texto se arma con los números de la tabla, así que cambia cuando
    el usuario modifica los filtros.

    Args:
        tabla: resultado de preparar_datos_evolucion.
        periodo: 'trimestral' o 'anual'.
        umbral_estable: variación (en puntos porcentuales) por debajo de
            la cual se dice que la tasa se mantuvo estable.

    Returns:
        Lista de oraciones (texto).
    """
    if tabla.empty:
        return ["No hay datos para la selección elegida."]
    datos = indicadores_principales(tabla, periodo)
    ultimo, primero = datos["periodo"], datos["periodo_inicial"]
    nombres = sorted(tabla["aglomerado_nombre"].unique())
    if len(nombres) <= 3:
        zona = ", ".join(nombres)
    else:
        zona = f"{len(nombres)} aglomerados"
    frases = [f"Considerando {zona}, la tasa de desempleo fue de "
              f"{formatear_numero(datos['tasa_total'])} % en {ultimo}."]

    variacion = datos["variacion_total"]
    if primero != ultimo and variacion == variacion:
        if abs(variacion) < umbral_estable:
            movimiento = "se mantuvo prácticamente estable"
        elif variacion > 0:
            movimiento = (
                f"subió {formatear_numero(variacion)} puntos porcentuales")
        else:
            movimiento = (
                f"bajó {formatear_numero(abs(variacion))} puntos porcentuales")
        frases.append(f"Respecto de {primero}, la tasa {movimiento}.")

    en_ultimo = tabla[(tabla["periodo"] == ultimo)
                      & (tabla["sexo"] == TOTAL_SEXO)]
    if len(en_ultimo) > 1:
        mayor = en_ultimo.loc[en_ultimo["tasa_desempleo"].idxmax()]
        menor = en_ultimo.loc[en_ultimo["tasa_desempleo"].idxmin()]
        frases.append(
            f"En {ultimo}, el mayor desempleo se dio en "
            f"{mayor['aglomerado_nombre']} "
            f"({formatear_numero(mayor['tasa_desempleo'])} %) y el menor en "
            f"{menor['aglomerado_nombre']} "
            f"({formatear_numero(menor['tasa_desempleo'])} %).")

    brecha = datos["brecha"]
    if brecha == brecha:
        if abs(brecha) < umbral_estable:
            frases.append(
                "Las tasas de mujeres y varones son prácticamente iguales.")
        else:
            quien = "mayor" if brecha > 0 else "menor"
            mujeres = formatear_numero(datos["tasa_mujer"])
            varones = formatear_numero(datos["tasa_varon"])
            frases.append(
                f"La tasa de las mujeres ({mujeres} %) es {quien} que la de "
                f"los varones ({varones} %): una brecha de "
                f"{formatear_numero(abs(brecha))} puntos porcentuales.")
    return frases