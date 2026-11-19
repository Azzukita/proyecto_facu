"""Parte C: análisis de tecnología (módulo Ciencia y Tecnología de la EPH).

Verifica la consistencia de los archivos (nombres de columnas e integridad
entre hogares e individuos) y calcula el porcentaje de hogares con celular,
internet y computadora por región y por aglomerado, ponderado con POND_TIC.
"""
from src import config, data_loader
from src.profiling import a_numero

RESPUESTA_SI = "si"
RESPUESTA_NO = "no"
RESPUESTA_SIN_DATO = "sin_dato"

# Indicadores del informe y la variable de hogares de la que salen. El
# celular no está en el archivo de hogares: sale de individuos.
INDICADORES = ("celular", "internet", "computadora")


def pares_por_anio(archivos):
    """Agrupa los archivos de tecnología por año.

    Args:
        archivos: lista de diccionarios devuelta por data_loader.

    Returns:
        Diccionario año -> {tipo: ruta}, con None si falta el archivo de
        hogares o el de individuos de ese año.
    """
    pares = {}
    for archivo in archivos:
        anio = archivo["anio"]
        if anio not in pares:
            pares[anio] = {config.TIPO_HOGAR: None,
                           config.TIPO_INDIVIDUO: None}
        pares[anio][archivo["tipo"]] = archivo["ruta"]
    return pares


def anios_consecutivos(anios):
    """Calcula la mayor cantidad de años consecutivos de una lista.

    Args:
        anios: años como texto, por ejemplo ['2022', '2023', '2024'].

    Returns:
        La longitud de la racha más larga de años consecutivos (0 si la
        lista está vacía).
    """
    numeros = sorted(set(int(anio) for anio in anios))
    mejor = 0
    actual = 0
    anterior = None
    for numero in numeros:
        if anterior is not None and numero == anterior + 1:
            actual += 1
        else:
            actual = 1
        mejor = max(mejor, actual)
        anterior = numero
    return mejor


def comparar_columnas(rutas):
    """Compara los nombres de columna de varios archivos contra el primero.

    El orden de las columnas no importa. Si un archivo no se puede leer, se
    informa como diferencia y se sigue con el siguiente.

    Args:
        rutas: lista de rutas a archivos del mismo tipo (hogares o
            individuos), uno por período.

    Returns:
        Diccionario con consistente (bool), archivos_comparados,
        referencia (nombre del primer archivo) y diferencias (por archivo,
        qué columnas faltan y cuáles sobran, o el error de lectura).
    """
    resultado = {"consistente": True, "archivos_comparados": len(rutas),
                 "referencia": None, "diferencias": []}
    if not rutas:
        return resultado
    resultado["referencia"] = rutas[0].name
    referencia = set(data_loader.leer_columnas(rutas[0]))
    for ruta in rutas[1:]:
        try:
            columnas = set(data_loader.leer_columnas(ruta))
        except (OSError, UnicodeDecodeError) as error:
            resultado["diferencias"].append(
                {"archivo": ruta.name, "error": str(error)})
            continue
        if columnas != referencia:
            resultado["diferencias"].append({
                "archivo": ruta.name,
                "faltan": sorted(referencia - columnas),
                "sobran": sorted(columnas - referencia),
            })
    resultado["consistente"] = not resultado["diferencias"]
    return resultado


def clave_hogar(fila):
    """Arma la tupla que identifica al hogar de una fila.

    Args:
        fila: diccionario de una fila de hogares o de individuos.

    Returns:
        La tupla (CODUSU, NRO_HOGAR, AGLOMERADO) con los valores sin
        espacios (config.COLS_ID_HOGAR).
    """
    return tuple((fila.get(col) or "").strip() for col in config.COLS_ID_HOGAR)


def validar_integridad(filas_hogares, filas_individuos):
    """Valida la integridad referencial entre hogares e individuos.

    Usa la tupla (CODUSU, NRO_HOGAR, AGLOMERADO) como identificador. Revisa
    que no haya hogares repetidos, individuos cuyo hogar no existe y
    hogares sin ningún individuo.

    Args:
        filas_hogares: filas del archivo de hogares.
        filas_individuos: filas del archivo de individuos.

    Returns:
        Diccionario con los totales, las inconsistencias encontradas e
        integridad_correcta (True si no hay ninguna).
    """
    claves_hogares = set()
    repetidos = 0
    for fila in filas_hogares:
        clave = clave_hogar(fila)
        if clave in claves_hogares:
            repetidos += 1
        claves_hogares.add(clave)
    claves_individuos = set()
    individuos_sin_hogar = 0
    for fila in filas_individuos:
        clave = clave_hogar(fila)
        claves_individuos.add(clave)
        if clave not in claves_hogares:
            individuos_sin_hogar += 1
    hogares_sin_individuos = len(claves_hogares - claves_individuos)
    return {
        "total_hogares": len(filas_hogares),
        "hogares_unicos": len(claves_hogares),
        "hogares_repetidos": repetidos,
        "total_individuos": len(filas_individuos),
        "individuos_sin_hogar": individuos_sin_hogar,
        "hogares_sin_individuos": hogares_sin_individuos,
        "integridad_correcta": (repetidos == 0 and individuos_sin_hogar == 0
                                and hogares_sin_individuos == 0),
    }


def _respuesta(valor):
    """Convierte un código del módulo TIC en si, no o sin dato."""
    valor = (valor or "").strip()
    if valor == config.TIC_SI:
        return RESPUESTA_SI
    if valor == config.TIC_NO:
        return RESPUESTA_NO
    return RESPUESTA_SIN_DATO


def celular_por_hogar(filas_individuos):
    """Determina qué hogares tienen celular a partir de sus integrantes.

    Un hogar tiene celular si AL MENOS UNA persona del hogar usó celular.
    Si nadie dijo que sí pero alguien dijo que no, no tiene. Si ninguna
    respuesta es válida (por ejemplo, código 9), queda sin dato.

    Args:
        filas_individuos: filas del archivo de individuos de tecnología.

    Returns:
        Diccionario tupla del hogar -> 'si', 'no' o 'sin_dato'.
    """
    resultado = {}
    for fila in filas_individuos:
        clave = clave_hogar(fila)
        actual = resultado.get(clave, RESPUESTA_SIN_DATO)
        respuesta = _respuesta(fila.get(config.COL_TIC_CELULAR))
        if respuesta == RESPUESTA_SI:
            actual = RESPUESTA_SI
        elif respuesta == RESPUESTA_NO and actual != RESPUESTA_SI:
            actual = RESPUESTA_NO
        resultado[clave] = actual
    return resultado


def _nuevo_acumulador():
    """Crea el acumulador vacío de un grupo (región, aglomerado o total)."""
    acumulador = {"muestra": 0, "ponderado": 0.0}
    for indicador in INDICADORES:
        acumulador[indicador] = {"si_w": 0.0, "validos_w": 0.0,
                                 "si_n": 0, "validos_n": 0, "sin_dato": 0}
    return acumulador


def _sumar_hogar(acumulador, respuestas, peso):
    """Suma un hogar (con su peso) a un acumulador."""
    acumulador["muestra"] += 1
    acumulador["ponderado"] += peso
    for indicador in INDICADORES:
        datos = acumulador[indicador]
        if respuestas[indicador] == RESPUESTA_SIN_DATO:
            datos["sin_dato"] += 1
            continue
        datos["validos_w"] += peso
        datos["validos_n"] += 1
        if respuestas[indicador] == RESPUESTA_SI:
            datos["si_w"] += peso
            datos["si_n"] += 1


def _porcentaje(parte, total):
    """Calcula un porcentaje con dos decimales (None si el total es 0)."""
    return round(100 * parte / total, 2) if total else None


def _resumir(nombre, acumulador):
    """Convierte un acumulador en el bloque que se informa."""
    bloque = {
        "nombre": nombre,
        "hogares_muestra": acumulador["muestra"],
        "hogares_ponderados": round(acumulador["ponderado"]),
    }
    for indicador in INDICADORES:
        datos = acumulador[indicador]
        bloque["pct_" + indicador] = _porcentaje(
            datos["si_w"], datos["validos_w"])
        bloque["pct_" + indicador + "_sin_ponderar"] = _porcentaje(
            datos["si_n"], datos["validos_n"])
        bloque["sin_dato_" + indicador] = datos["sin_dato"]
    return bloque


def calcular_penetracion(filas_hogares, celular):
    """Calcula el % de hogares con celular, internet y computadora.

    Se pondera con POND_TIC. Cada indicador se calcula sobre los hogares
    con dato válido (los sin dato se excluyen del denominador y se cuentan
    aparte). La región se obtiene del aglomerado (config.REGION_DE_AGLOMERADO).
    Los hogares sin peso válido se descartan y se cuentan.

    Args:
        filas_hogares: filas del archivo de hogares de tecnología.
        celular: resultado de celular_por_hogar.

    Returns:
        Diccionario con total, por_region y por_aglomerado (cada bloque con
        nombre, hogares, porcentajes ponderados y sin ponderar, y hogares
        sin dato), más sin_peso y sin_region.
    """
    total = _nuevo_acumulador()
    regiones = {}
    aglomerados = {}
    sin_peso = 0
    sin_region = 0
    for fila in filas_hogares:
        peso = a_numero(fila.get(config.COL_POND_TIC))
        if peso is None or peso <= 0:
            sin_peso += 1
            continue
        clave = clave_hogar(fila)
        aglomerado = clave[2].lstrip("0")
        region = config.REGION_DE_AGLOMERADO.get(aglomerado)
        if region is None:
            sin_region += 1
            region = "sin_region"
        respuestas = {
            "celular": celular.get(clave, RESPUESTA_SIN_DATO),
            "internet": _respuesta(fila.get(config.COL_TIC_INTERNET)),
            "computadora": _respuesta(fila.get(config.COL_TIC_COMPUTADORA)),
        }
        if region not in regiones:
            regiones[region] = _nuevo_acumulador()
        if aglomerado not in aglomerados:
            aglomerados[aglomerado] = _nuevo_acumulador()
        for acumulador in (total, regiones[region], aglomerados[aglomerado]):
            _sumar_hogar(acumulador, respuestas, peso)
    por_region = {}
    for codigo in sorted(regiones, key=_orden_codigo):
        nombre = config.NOMBRES_REGIONES.get(codigo, "Sin región")
        por_region[codigo] = _resumir(nombre, regiones[codigo])
    por_aglomerado = {}
    for codigo in sorted(aglomerados, key=_orden_codigo):
        nombre = config.AGLOMERADOS.get(codigo, codigo)
        por_aglomerado[codigo] = _resumir(nombre, aglomerados[codigo])
    return {
        "total": _resumir("Total aglomerados EPH", total),
        "por_region": por_region,
        "por_aglomerado": por_aglomerado,
        "sin_peso": sin_peso,
        "sin_region": sin_region,
    }


def _orden_codigo(codigo):
    """Ordena códigos numéricos como número y deja al final los demás."""
    return (0, int(codigo)) if codigo.isdigit() else (1, 0)


def armar_informe_tecnologia(resultados_por_anio, metadatos=None):
    """Arma el informe de tecnología para exportar a JSON.

    Args:
        resultados_por_anio: diccionario año -> resultado de
            calcular_penetracion (con la integridad agregada).
        metadatos: diccionario con datos del análisis que se copia tal cual.

    Returns:
        Diccionario con metadatos, notas de cómo se calculó y los
        resultados de cada año.
    """
    return {
        "metadatos": metadatos or {},
        "notas": config.NOTAS_TECNOLOGIA,
        "anios": resultados_por_anio,
    }
