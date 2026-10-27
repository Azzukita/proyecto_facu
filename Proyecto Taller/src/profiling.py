"""Funciones de análisis de calidad de datos (Data Profiling)."""
from src import config
 
# Resultados posibles al clasificar un valor.
RESULTADO_VALIDO = "valido"
RESULTADO_FALTANTE = "faltante_real"
RESULTADO_NO_CORRESPONDE = "no_corresponde"


# esta funcion clasifica un valor de una columna
# como valido, faltante o no corresponde
def clasificar_valor(valor, columna):
    """Clasifica un valor leído del archivo según las reglas de config.py.
 
    Primero se consulta NO_CORRESPONDE, porque tiene prioridad: en algunas
    columnas el vacío significa "no corresponde" y no "faltante".
 
    Args:
        valor: texto leído del archivo (puede ser None si la fila estaba
            incompleta).
        columna: nombre de la columna a la que pertenece el valor.
 
    Returns:
        RESULTADO_NO_CORRESPONDE si la pregunta no aplica,
        RESULTADO_FALTANTE si es un faltante real, o
        RESULTADO_VALIDO en cualquier otro caso.
    """
    valor = (valor or "").strip()
    if valor in config.NO_CORRESPONDE.get(columna, ()):
        return RESULTADO_NO_CORRESPONDE
    codigos_faltantes = config.FALTANTES_REALES.get(columna, ())
    if valor == config.VALOR_VACIO or valor in codigos_faltantes:
        return RESULTADO_FALTANTE
    return RESULTADO_VALIDO

# recibe una lista de filas y un conjunto de columnas
# y devuelve un diccionario con la cantidad de valores válidos, 
# faltantes reales y no corresponde por columna,
# así como la cantidad de filas y las columnas inexistentes.
def contar_valores(filas, columnas):
    """Cuenta, por columna, los valores válidos, faltantes y no corresponde.
 
    Solo cuenta: no calcula porcentajes ni aplica umbrales. Así el conteo se
    hace una sola vez y se puede reutilizar con distintos umbrales o sumar
    con el de otros trimestres.
 
    Args:
        filas: lista de diccionarios (ver data_loader.leer_filas).
        columnas: nombres de las columnas a analizar.
 
    Returns:
        Diccionario con total_filas, columnas (por columna: validos,
        faltantes_reales y no_corresponde) e inexistentes (columnas pedidas
        que no están en el archivo).
    """
    total = len(filas)
    existentes = list(filas[0].keys()) if filas else []
    conteos = {}
    inexistentes = []
    for columna in columnas:
        if columna not in existentes:
            inexistentes.append(columna)
            continue
        cuenta = {
            RESULTADO_VALIDO: 0,
            RESULTADO_FALTANTE: 0,
            RESULTADO_NO_CORRESPONDE: 0,
        }
        for fila in filas:
            cuenta[clasificar_valor(fila.get(columna), columna)] += 1
        conteos[columna] = {
            "validos": cuenta[RESULTADO_VALIDO],
            "faltantes_reales": cuenta[RESULTADO_FALTANTE],
            "no_corresponde": cuenta[RESULTADO_NO_CORRESPONDE],
        }
    return {
        "total_filas": total,
        "columnas": conteos,
        "inexistentes": inexistentes,
    }

# recibe una lista de resultados de contar_valores
# y devuelve un resultado equivalente a contar_valores
# con la suma de los conteos de cada columna
# una columna que falte en alguno de los períodos se informa como inexistente
# y se excluye de la suma, para que los totales sean coherentes

def sumar_conteos(lista_conteos):
    """Suma los conteos de varios períodos (por ejemplo, 4 trimestres).
 
    Se suman los conteos y no los porcentajes: promediar porcentajes da un
    resultado distinto cuando los trimestres tienen distinta cantidad de
    filas. Una columna que falte en alguno de los períodos se informa como
    inexistente y se excluye de la suma, para que los totales sean coherentes.
 
    Args:
        lista_conteos: lista de resultados de contar_valores.
 
    Returns:
        Un diccionario con el mismo formato que contar_valores.
    """
    total = 0
    inexistentes = []
    for conteos in lista_conteos:
        total += conteos["total_filas"]
        for columna in conteos["inexistentes"]:
            if columna not in inexistentes:
                inexistentes.append(columna)
    columnas = {}
    if lista_conteos:
        for columna in lista_conteos[0]["columnas"]:
            if columna in inexistentes:
                continue
            suma = {"validos": 0, "faltantes_reales": 0, "no_corresponde": 0}
            for conteos in lista_conteos:
                for clave in suma:
                    suma[clave] += conteos["columnas"][columna][clave]
            columnas[columna] = suma
    return {
        "total_filas": total,
        "columnas": columnas,
        "inexistentes": inexistentes,
    }


def completitud_con_umbral(conteos, umbral=None):
    """Calcula porcentajes y aplica un umbral de faltantes a unos conteos.
 
    Los porcentajes se calculan sobre el total de filas. Una columna supera
    el umbral si su porcentaje de faltantes reales es MAYOR (no igual) al
    umbral.
 
    Args:
        conteos: resultado de contar_valores o de sumar_conteos.
        umbral: porcentaje de faltantes (por defecto
            config.UMBRAL_FALTANTES_PCT).
 
    Returns:
        Diccionario con total_filas, umbral_pct, columnas (conteos,
        porcentajes y si supera el umbral), sobre_umbral (lista de columnas
        que lo superan), mayor_faltante (TODAS las columnas empatadas con la
        mayor cantidad de faltantes; vacía si nadie tiene faltantes),
        pct_mayor_faltante e inexistentes.
    """
    if umbral is None:
        umbral = config.UMBRAL_FALTANTES_PCT
    total = conteos["total_filas"]
    columnas = {}
    mayor_cantidad = 0
    for columna, c in conteos["columnas"].items():
        pct_faltantes = 100 * c["faltantes_reales"] / total if total else 0.0
        pct_validos = 100 * c["validos"] / total if total else 0.0
        pct_no_corr = 100 * c["no_corresponde"] / total if total else 0.0
        columnas[columna] = {
            "validos": c["validos"],
            "faltantes_reales": c["faltantes_reales"],
            "no_corresponde": c["no_corresponde"],
            "pct_validos": round(pct_validos, 2),
            "pct_faltantes": round(pct_faltantes, 2),
            "pct_no_corresponde": round(pct_no_corr, 2),
            "supera_umbral": pct_faltantes > umbral,
        }
        if c["faltantes_reales"] > mayor_cantidad:
            mayor_cantidad = c["faltantes_reales"]
    sobre_umbral = [col for col, d in columnas.items() if d["supera_umbral"]]
    mayor_faltante = []
    if mayor_cantidad > 0:
        mayor_faltante = [
            col for col, c in conteos["columnas"].items()
            if c["faltantes_reales"] == mayor_cantidad
        ]
    pct_mayor = round(100 * mayor_cantidad / total, 2) if total else 0.0
    return {
        "total_filas": total,
        "umbral_pct": umbral,
        "columnas": columnas,
        "sobre_umbral": sobre_umbral,
        "mayor_faltante": mayor_faltante,
        "pct_mayor_faltante": pct_mayor,
        "inexistentes": conteos["inexistentes"],
    }


# recibe una lista de filas y un conjunto de columnas
# y devuelve un diccionario con la cantidad de valores válidos,
# faltantes reales y no corresponde por columna,
# así como el porcentaje de faltantes y si supera el umbral.
def contar_completitud(filas, columnas, umbral=None):
    """Cuenta y aplica el umbral en un solo paso (para un único período).
 
    Es contar_valores seguido de completitud_con_umbral.
 
    Args:
        filas: lista de diccionarios (ver data_loader.leer_filas).
        columnas: nombres de las columnas a analizar.
        umbral: porcentaje de faltantes (por defecto
            config.UMBRAL_FALTANTES_PCT).
 
    Returns:
        Lo mismo que completitud_con_umbral.
    """
    return completitud_con_umbral(contar_valores(filas, columnas), umbral)
 

# esta funcion arma un informe de completitud por trimestre y por año 
def armar_informe_completitud(resultados, umbral, metadatos=None):
    """Arma el informe de completitud para un umbral, por trimestre y por año.
 
    Args:
        resultados: lista de diccionarios con las claves anio, trimestre y
            conteos (resultado de contar_valores), uno por archivo.
        umbral: porcentaje de faltantes a aplicar.
        metadatos: diccionario con datos del análisis (categoría, tipo de
            archivo, años) que se copia tal cual al informe.
 
    Returns:
        Diccionario con metadatos, umbral_pct, por_trimestre (un bloque por
        cada 'año-trimestre'), anual (un bloque por año, calculado sumando
        los conteos de sus trimestres) y notas de las columnas analizadas.
    """
    por_trimestre = {}
    conteos_por_anio = {}
    trimestres_por_anio = {}
    for resultado in resultados:
        anio = resultado["anio"]
        periodo = anio + "-" + resultado["trimestre"]
        por_trimestre[periodo] = completitud_con_umbral(
            resultado["conteos"], umbral)
        if anio not in conteos_por_anio:
            conteos_por_anio[anio] = []
            trimestres_por_anio[anio] = []
        conteos_por_anio[anio].append(resultado["conteos"])
        trimestres_por_anio[anio].append(resultado["trimestre"])
    anual = {}
    for anio, lista in conteos_por_anio.items():
        anual[anio] = completitud_con_umbral(sumar_conteos(lista), umbral)
        anual[anio]["trimestres_incluidos"] = trimestres_por_anio[anio]
    notas = {}
    if resultados:
        for columna in resultados[0]["conteos"]["columnas"]:
            if columna in config.NOTAS_COLUMNAS:
                notas[columna] = config.NOTAS_COLUMNAS[columna]
    return {
        "metadatos": metadatos or {},
        "umbral_pct": umbral,
        "por_trimestre": por_trimestre,
        "anual": anual,
        "notas": notas,
    }


# =============================================================================
# AUXILIARES (Requerimientos A.2 y A.3)
# =============================================================================
def frecuencias(filas, columna):
    """Cuenta cuántas veces aparece cada valor de una columna.

    Args:
        filas: lista de diccionarios (ver data_loader.leer_filas).
        columna: nombre de la columna.

    Returns:
        Diccionario valor -> cantidad. Los vacíos se informan como
        '(vacío)' y las filas sin la columna como '(columna ausente)'.
    """
    conteo = {}
    for fila in filas:
        valor = fila.get(columna)
        if valor is None:
            valor = "(columna ausente)"
        elif valor.strip() == "":
            valor = "(vacío)"
        conteo[valor] = conteo.get(valor, 0) + 1
    return conteo


# esta funcion convierte un texto del archivo en número
# acepta signo y coma decimal (por ejemplo '-9' o '1500,50')
def a_numero(valor):
    """Convierte un texto del archivo en número.

    Acepta signo y coma decimal (por ejemplo '-9' o '1500,50').

    Args:
        valor: texto leído del archivo (puede ser None).

    Returns:
        El número (int si no tiene decimales, float si los tiene) o None
        si el texto está vacío o no es un número.
    """
    texto = (valor or "").strip().replace(",", ".")
    if texto == "":
        return None
    try:
        numero = float(texto)
    except ValueError:
        return None
    if numero == int(numero):
        return int(numero)
    return numero


# esta funcion indica si un valor está dentro de un rango, con opción de incluir o no los extremos
def en_rango(valor, minimo, maximo, incluidos=None):
    """Indica si un valor está dentro de un rango.

    Args:
        valor: número a evaluar (None devuelve False).
        minimo: límite inferior.
        maximo: límite superior (None = sin límite).
        incluidos: si los extremos cuentan como dentro del rango (por
            defecto config.EXTREMOS_INCLUIDOS).

    Returns:
        True si el valor está dentro del rango.
    """
    if valor is None:
        return False
    if incluidos is None:
        incluidos = config.EXTREMOS_INCLUIDOS
    if incluidos:
        return valor >= minimo and (maximo is None or valor <= maximo)
    return valor > minimo and (maximo is None or valor < maximo)


def _valor(fila, columna):
    """Devuelve el valor de una columna sin espacios ('' si no está)."""
    return (fila.get(columna) or "").strip()


def _edad(fila):
    """Devuelve la edad (CH06) como número, o None si no es válida."""
    return a_numero(fila.get(config.COL_EDAD))


def _es_jubilado(fila):
    """Indica si la persona figura como jubilada/pensionada (CAT_INAC)."""
    return _valor(fila, config.COL_CAT_INAC) == config.CAT_INAC_JUBILADO


# esta función arma un ejemplo de inconsistencia que identifica a la persona
def armar_ejemplo(fila, columnas):
    """Arma un ejemplo de inconsistencia que identifica a la persona.

    Args:
        fila: diccionario de una fila.
        columnas: columnas de la regla, que se agregan al ejemplo.

    Returns:
        Diccionario con las columnas de identificación, del período y de
        la regla.
    """
    ejemplo = {}
    for columna in (config.COLS_IDENTIFICACION + config.COLS_PERIODO
                    + tuple(columnas)):
        ejemplo[columna] = _valor(fila, columna)
    return ejemplo

# =============================================================================
# REGLAS (Requerimientos A.2 y A.3, Modificación 5)
# =============================================================================
# Cada regla recibe una fila y devuelve True si encuentra la inconsistencia.
# Los valores de corte salen de config.py: para cambiar una edad o un código
# no habría que tocar las funciones estas 

def _edad_invalida(fila):
    """CRÍTICO: la edad está vacía o no es un número."""
    return _edad(fila) is None


def _menor_no_inactivo(fila):
    """A.2.1: edad en el rango de ERROR y estado distinto de inactivo."""
    estado = _valor(fila, config.COL_ESTADO)
    if estado in (config.ESTADO_INACTIVO, config.ESTADO_NO_REALIZADA):
        return False
    return en_rango(_edad(fila), config.EDAD_MIN_ERROR, config.EDAD_MAX_ERROR)


def _mayor_con_categoria_activa(fila):
    """A.2.2: edad mayor o igual a EDAD_MIN_VERIFICAR con CAT_OCUP activa."""
    return (_valor(fila, config.COL_CAT_OCUP) in config.CAT_OCUP_ACTIVAS
            and en_rango(_edad(fila), config.EDAD_MIN_VERIFICAR, None))


def _ocupado_menor_edad_legal(fila):
    """A.2.3: ocupado por debajo de la edad legal para trabajar."""
    # Solo la franja entre EDAD_MAX_ERROR y la edad legal (sin incluirla):
    # de EDAD_LEGAL_TRABAJO en adelante es legal y hasta EDAD_MAX_ERROR ya
    # es ERROR.
    edad = _edad(fila)
    return (_valor(fila, config.COL_ESTADO) == config.ESTADO_OCUPADO
            and edad is not None
            and config.EDAD_MAX_ERROR < edad < config.EDAD_LEGAL_TRABAJO)


def _jubilado_menor_30(fila):
    """A.2.4: jubilado/pensionado menor a EDAD_MIN_JUBILADO."""
    edad = _edad(fila)
    return (_es_jubilado(fila) and edad is not None
            and edad < config.EDAD_MIN_JUBILADO)


def _edad_outlier(fila):
    """ADVERTENCIA: edad mayor o igual a EDAD_OUTLIER."""
    return en_rango(_edad(fila), config.EDAD_OUTLIER, None)


def _entrevista_no_realizada(fila):
    """CRÍTICO: ESTADO = 0 (entrevista individual no realizada)."""
    return _valor(fila, config.COL_ESTADO) == config.ESTADO_NO_REALIZADA


def _ocupado_sin_cat_ocup(fila):
    """A.3.1: ocupado sin categoría ocupacional válida."""
    # CAT_OCUP vacío, 0 o 9 (NS/NR): a un ocupado le corresponde 1 a 4.
    return (_valor(fila, config.COL_ESTADO) == config.ESTADO_OCUPADO
            and _valor(fila, config.COL_CAT_OCUP)
            not in config.CAT_OCUP_ACTIVAS)


def _desocupado_con_ingreso(fila):
    """A.3.2: desocupado con ingreso de la ocupación principal."""
    ingreso = a_numero(fila.get(config.COL_INGRESO))
    return (_valor(fila, config.COL_ESTADO) == config.ESTADO_DESOCUPADO
            and ingreso is not None and ingreso > 0)


def _activo_con_cat_inac(fila):
    """A.3.3: ocupado o desocupado con categoría de inactividad."""
    # CAT_INAC solo aplica a inactivos; en activos tiene que ser 0.
    cat_inac = _valor(fila, config.COL_CAT_INAC)
    return (_valor(fila, config.COL_ESTADO) in config.ESTADOS_ACTIVOS
            and cat_inac not in config.NO_CORRESPONDE[config.COL_CAT_INAC]
            and cat_inac != config.VALOR_VACIO)


def _ocupado_sin_ingreso(fila):
    """A.3.4: ocupado sin ingreso que no es trabajador familiar."""
    # El trabajador familiar sin remuneración puede legítimamente no cobrar.
    ingreso = a_numero(fila.get(config.COL_INGRESO))
    return (_valor(fila, config.COL_ESTADO) == config.ESTADO_OCUPADO
            and _valor(fila, config.COL_CAT_OCUP)
            != config.CAT_OCUP_TRABAJADOR_FAMILIAR
            and ingreso == 0)


def _universitario_menor(fila):
    """Mod. 5.1: nivel universitario con edad menor a EDAD_MIN_UNIVERSITARIO."""
    edad = _edad(fila)
    return (_valor(fila, config.COL_NIVEL_ED) in config.NIVEL_ED_UNIVERSITARIO
            and edad is not None and edad < config.EDAD_MIN_UNIVERSITARIO)


def _jubilado_antes_de_edad(fila):
    """Mod. 5.2: jubilado menor a la edad de jubilación de su sexo."""
    edad = _edad(fila)
    edad_minima = config.EDAD_MIN_JUBILACION_POR_SEXO.get(
        _valor(fila, config.COL_SEXO))
    return (_es_jubilado(fila) and edad is not None
            and edad_minima is not None and edad < edad_minima)


def _desocupado_con_otras_ocupaciones(fila):
    """INFO: desocupado con ingreso de otras ocupaciones."""
    ingreso = a_numero(fila.get(config.COL_INGRESO_OTRAS))
    return (_valor(fila, config.COL_ESTADO) == config.ESTADO_DESOCUPADO
            and ingreso is not None and ingreso > 0)


def _desocupado_con_ingreso_total(fila):
    """INFO: desocupado con ingreso total individual mayor a 0."""
    ingreso = a_numero(fila.get(config.COL_INGRESO_TOTAL))
    return (_valor(fila, config.COL_ESTADO) == config.ESTADO_DESOCUPADO
            and ingreso is not None and ingreso > 0)


# esta funcion arma un diccionario con los datos de una regla de consistencia
# cada regla tiene un nombre, un requerimiento, una etiqueta, una descripción,
# una lista de columnas que intervienen, una función que evalúa la regla
# y, opcionalmente, una columna por la que se desagregan los casos
def _regla(nombre, requerimiento, etiqueta, descripcion, columnas, cumple,
           desagregar_por=None):
    """Arma el diccionario que describe una regla de consistencia.

    Args:
        nombre: identificador corto de la regla.
        requerimiento: requerimiento al que pertenece (por ejemplo 'A.2.1').
        etiqueta: una de las etiquetas de config.ORDEN_ETIQUETAS.
        descripcion: texto que explica la inconsistencia.
        columnas: columnas que intervienen (las usa el informe por roles).
        cumple: función que recibe una fila y devuelve True si la regla se
            cumple.
        desagregar_por: columna por la que se cuentan los casos además del
            total (por ejemplo config.COL_SEXO); None = sin desagregar.

    Returns:
        Diccionario con los datos de la regla.
    """
    return {
        "nombre": nombre,
        "requerimiento": requerimiento,
        "etiqueta": etiqueta,
        "descripcion": descripcion,
        "columnas": list(columnas),
        "cumple": cumple,
        "desagregar_por": desagregar_por,
    }


# Para agregar una regla alcanza con sumar una entrada a la lista.
REGLAS_A2 = [
    _regla("menor_no_inactivo", "A.2.1", config.ETIQUETA_ERROR,
           f"Edad entre {config.EDAD_MIN_ERROR} y {config.EDAD_MAX_ERROR} "
           "años con estado distinto de inactivo",
           (config.COL_EDAD, config.COL_ESTADO), _menor_no_inactivo),
    _regla("mayor_con_categoria_activa", "A.2.2", config.ETIQUETA_VERIFICAR,
           f"Edad de {config.EDAD_MIN_VERIFICAR} años o más con categoría "
           "ocupacional activa",
           (config.COL_EDAD, config.COL_CAT_OCUP),
           _mayor_con_categoria_activa),
    _regla("ocupado_menor_edad_legal", "A.2.3", config.ETIQUETA_VERIFICAR,
           f"Ocupado mayor de {config.EDAD_MAX_ERROR} y menor de "
           f"{config.EDAD_LEGAL_TRABAJO} años (edad legal para trabajar)",
           (config.COL_EDAD, config.COL_ESTADO), _ocupado_menor_edad_legal),
    _regla("jubilado_menor_30", "A.2.4", config.ETIQUETA_VERIFICAR,
           f"Jubilado/pensionado menor de {config.EDAD_MIN_JUBILADO} años",
           (config.COL_EDAD, config.COL_CAT_INAC), _jubilado_menor_30),
    _regla("edad_invalida", "Mod. 5.3", config.ETIQUETA_CRITICO,
           "Edad vacía o no numérica: no se pueden evaluar las reglas de edad",
           (config.COL_EDAD,), _edad_invalida),
    _regla("edad_outlier", "Mod. 5.3", config.ETIQUETA_ADVERTENCIA,
           f"Edad de {config.EDAD_OUTLIER} años o más (valor raro)",
           (config.COL_EDAD,), _edad_outlier),
]

REGLAS_A3 = [
    _regla("ocupado_sin_cat_ocup", "A.3.1", config.ETIQUETA_ERROR,
           "Ocupado con CAT_OCUP faltante (vacío, 0 o 9)",
           (config.COL_ESTADO, config.COL_CAT_OCUP), _ocupado_sin_cat_ocup),
    _regla("desocupado_con_ingreso", "A.3.2", config.ETIQUETA_VERIFICAR,
           f"Desocupado con ingreso de la ocupación principal "
           f"({config.COL_INGRESO} > 0)",
           (config.COL_ESTADO, config.COL_INGRESO), _desocupado_con_ingreso),
    _regla("activo_con_cat_inac", "A.3.3", config.ETIQUETA_ERROR,
           "Ocupado o desocupado con categoría de inactividad",
           (config.COL_ESTADO, config.COL_CAT_INAC), _activo_con_cat_inac),
    _regla("ocupado_sin_ingreso", "A.3.4", config.ETIQUETA_VERIFICAR,
           f"Ocupado con {config.COL_INGRESO} = 0 que no es trabajador "
           "familiar sin remuneración",
           (config.COL_ESTADO, config.COL_INGRESO, config.COL_CAT_OCUP),
           _ocupado_sin_ingreso),
    _regla("universitario_menor", "Mod. 5.1", config.ETIQUETA_ERROR,
           f"Nivel educativo universitario con menos de "
           f"{config.EDAD_MIN_UNIVERSITARIO} años",
           (config.COL_NIVEL_ED, config.COL_EDAD), _universitario_menor),
    _regla("jubilado_antes_de_edad", "Mod. 5.2", config.ETIQUETA_VERIFICAR,
           "Jubilado/pensionado menor a la edad de jubilación según sexo",
           (config.COL_CAT_INAC, config.COL_EDAD, config.COL_SEXO),
           _jubilado_antes_de_edad, desagregar_por=config.COL_SEXO),
    _regla("entrevista_no_realizada", "Mod. 5.3", config.ETIQUETA_CRITICO,
           "ESTADO = 0: entrevista individual no realizada; se recomienda "
           "no usar el registro",
           (config.COL_ESTADO,), _entrevista_no_realizada),
    _regla("desocupado_con_otras_ocupaciones", "Mod. 5.3",
           config.ETIQUETA_INFO,
           f"Desocupado con ingreso de otras ocupaciones "
           f"({config.COL_INGRESO_OTRAS} > 0)",
           (config.COL_ESTADO, config.COL_INGRESO_OTRAS),
           _desocupado_con_otras_ocupaciones),
    _regla("desocupado_con_ingreso_total", "Mod. 5.3", config.ETIQUETA_INFO,
           f"Desocupado con ingreso total individual "
           f"({config.COL_INGRESO_TOTAL} > 0; puede venir de jubilación, "
           "subsidios, etc.)",
           (config.COL_ESTADO, config.COL_INGRESO_TOTAL),
           _desocupado_con_ingreso_total),
]



# =============================================================================
# EVALUACIÓN E INFORMES (Requerimientos A.2 y A.3, Modificación 5)
# =============================================================================
def evaluar_reglas(filas, reglas, max_ejemplos=None):
    """Aplica reglas de consistencia a las filas de un período.

    Solo cuenta casos y guarda ejemplos: igual que contar_valores, el
    resultado se puede sumar con el de otros trimestres.

    Args:
        filas: lista de diccionarios (ver data_loader.leer_filas).
        reglas: lista de reglas (por ejemplo REGLAS_A2 + REGLAS_A3).
        max_ejemplos: ejemplos a guardar por regla (por defecto
            config.MAX_EJEMPLOS).

    Returns:
        Diccionario con total_filas y reglas (por nombre: requerimiento,
        etiqueta, descripcion, columnas, cantidad, ejemplos y, si la regla
        lo pide, desagregado con la cantidad por valor de esa columna).
    """
    if max_ejemplos is None:
        max_ejemplos = config.MAX_EJEMPLOS
    resultado = {}
    for regla in reglas:
        resultado[regla["nombre"]] = {
            "requerimiento": regla["requerimiento"],
            "etiqueta": regla["etiqueta"],
            "descripcion": regla["descripcion"],
            "columnas": regla["columnas"],
            "cantidad": 0,
            "ejemplos": [],
        }
        if regla["desagregar_por"]:
            resultado[regla["nombre"]]["desagregado_por"] = (
                regla["desagregar_por"])
            resultado[regla["nombre"]]["desagregado"] = {}
    for fila in filas:
        for regla in reglas:
            if not regla["cumple"](fila):
                continue
            datos = resultado[regla["nombre"]]
            datos["cantidad"] += 1
            if len(datos["ejemplos"]) < max_ejemplos:
                datos["ejemplos"].append(
                    armar_ejemplo(fila, regla["columnas"]))
            if regla["desagregar_por"]:
                valor = _valor(fila, regla["desagregar_por"])
                datos["desagregado"][valor] = (
                    datos["desagregado"].get(valor, 0) + 1)
    return {"total_filas": len(filas), "reglas": resultado}


# esta funcion suma los resultados de evaluar_reglas de varios períodos
def sumar_hallazgos(lista_hallazgos, max_ejemplos=None):
    """Suma los resultados de evaluar_reglas de varios períodos.

    Se suman las cantidades y se conservan los primeros ejemplos (cada
    ejemplo lleva su año y trimestre, así que se sabe de dónde salió).

    Args:
        lista_hallazgos: lista de resultados de evaluar_reglas.
        max_ejemplos: ejemplos a conservar por regla (por defecto
            config.MAX_EJEMPLOS).

    Returns:
        Un diccionario con el mismo formato que evaluar_reglas.
    """
    if max_ejemplos is None:
        max_ejemplos = config.MAX_EJEMPLOS
    total = 0
    reglas = {}
    for hallazgos in lista_hallazgos:
        total += hallazgos["total_filas"]
        for nombre, datos in hallazgos["reglas"].items():
            if nombre not in reglas:
                reglas[nombre] = dict(datos)
                reglas[nombre]["ejemplos"] = list(datos["ejemplos"])
                if "desagregado" in datos:
                    reglas[nombre]["desagregado"] = dict(datos["desagregado"])
                continue
            suma = reglas[nombre]
            suma["cantidad"] += datos["cantidad"]
            lugar = max_ejemplos - len(suma["ejemplos"])
            suma["ejemplos"] += datos["ejemplos"][:max(lugar, 0)]
            for valor, cantidad in datos.get("desagregado", {}).items():
                suma["desagregado"][valor] = (
                    suma["desagregado"].get(valor, 0) + cantidad)
    return {"total_filas": total, "reglas": reglas}


# esta funcion ordena las reglas por gravedad según config.ORDEN_ETIQUETAS
def ordenar_por_gravedad(reglas):
    """Devuelve los nombres de las reglas ordenados de mayor a menor gravedad.

    Args:
        reglas: diccionario 'reglas' de evaluar_reglas o sumar_hallazgos.

    Returns:
        Lista de nombres, ordenada según config.ORDEN_ETIQUETAS (las reglas
        con la misma etiqueta mantienen su orden).
    """
    return sorted(reglas, key=lambda nombre: config.ORDEN_ETIQUETAS.index(
        reglas[nombre]["etiqueta"]))


# esta funcion arma un informe de consistencia por trimestre y por año
def armar_informe_consistencia(resultados, metadatos=None):
    """Arma el informe de consistencia por trimestre y por año.

    Args:
        resultados: lista de diccionarios con las claves anio, trimestre y
            hallazgos (resultado de evaluar_reglas), uno por archivo.
        metadatos: diccionario con datos del análisis que se copia tal cual.

    Returns:
        Diccionario con metadatos, criterios_etiquetas, por_trimestre (un
        bloque por 'año-trimestre') y anual (un bloque por año). Dentro de
        cada bloque las reglas van ordenadas por gravedad.
    """
    por_trimestre = {}
    por_anio = {}
    for resultado in resultados:
        periodo = resultado["anio"] + "-" + resultado["trimestre"]
        por_trimestre[periodo] = _ordenar_bloque(resultado["hallazgos"])
        if resultado["anio"] not in por_anio:
            por_anio[resultado["anio"]] = []
        por_anio[resultado["anio"]].append(resultado)
    anual = {}
    for anio, lista in por_anio.items():
        suma = sumar_hallazgos([r["hallazgos"] for r in lista])
        anual[anio] = _ordenar_bloque(suma)
        anual[anio]["trimestres_incluidos"] = [r["trimestre"] for r in lista]
    return {
        "metadatos": metadatos or {},
        "criterios_etiquetas": {
            config.ETIQUETA_CRITICO: "Invalida el registro o la columna; "
                                     "se recomienda no usarlo.",
            config.ETIQUETA_ERROR: "Contradicción lógica entre variables.",
            config.ETIQUETA_VERIFICAR: "Caso raro que puede ser legítimo; "
                                       "requiere revisión.",
            config.ETIQUETA_ADVERTENCIA: "Situación inusual pero posible.",
            config.ETIQUETA_INFO: "Observación para documentar.",
        },
        "por_trimestre": por_trimestre,
        "anual": anual,
    }

# esta funcion ordena las reglas por gravedad según config.ORDEN_ETIQUETAS
# y devuelve un bloque con las reglas ordenadas
def _ordenar_bloque(hallazgos):
    """Copia un resultado de evaluar_reglas con las reglas por gravedad."""
    ordenadas = {}
    for nombre in ordenar_por_gravedad(hallazgos["reglas"]):
        ordenadas[nombre] = hallazgos["reglas"][nombre]
    return {"total_filas": hallazgos["total_filas"], "reglas": ordenadas}


# esta funcion arma un informe de inconsistencias por rol de usuario
def informe_por_roles(hallazgos, roles=None):
    """Arma el informe de inconsistencias según los roles de usuario.

    Para cada rol y cada columna que le interesa, junta las reglas que usan
    esa columna y cuyas etiquetas cuentan como inconsistencia
    (config.ETIQUETAS_INCONSISTENCIA).

    Args:
        hallazgos: resultado de evaluar_reglas o sumar_hallazgos.
        roles: diccionario rol -> columnas (por defecto config.ROLES).

    Returns:
        Diccionario rol -> {columnas: {columna: {casos, reglas}},
        tiene_inconsistencias}. 'casos' suma los casos de cada regla, así
        que una persona con dos inconsistencias en la misma columna cuenta
        dos veces.
    """
    roles = roles or config.ROLES
    informe = {}
    for rol, columnas_rol in roles.items():
        columnas = {}
        for columna in columnas_rol:
            casos = 0
            reglas = {}
            for nombre, datos in hallazgos["reglas"].items():
                if (columna in datos["columnas"]
                        and datos["etiqueta"]
                        in config.ETIQUETAS_INCONSISTENCIA):
                    casos += datos["cantidad"]
                    reglas[nombre] = {
                        "etiqueta": datos["etiqueta"],
                        "cantidad": datos["cantidad"],
                    }
            columnas[columna] = {"casos": casos, "reglas": reglas}
        informe[rol] = {
            "columnas": columnas,
            "tiene_inconsistencias": [
                col for col, d in columnas.items() if d["casos"] > 0],
        }
    return informe