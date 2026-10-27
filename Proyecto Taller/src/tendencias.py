"""Requerimiento B.1: tendencias del mercado laboral por aglomerado.

Calcula, para cada aglomerado elegido, la tasa de desempleo y la
distribución de la población entre ocupados, desocupados e inactivos.
Todo se pondera con PONDERA y se desagrega por sexo (CH04) y por rango
etario (CH06), por trimestre, por semestre y por año (Modificación 6).
"""
from src import config
from src.profiling import a_numero

# Grupos en los que se desagrega cada aglomerado.
GRUPO_TOTAL = "total"
GRUPO_SEXO = "por_sexo"
GRUPO_RANGO = "por_rango_etario"


def interpretar_anios(texto, disponibles):
    """Convierte lo que escribe el usuario en una lista de años.

    Acepta un año ('2024'), un rango ('2023-2025') o una lista separada
    por comas ('2023, 2025'). Si el texto está vacío, devuelve todos los
    años disponibles.

    Args:
        texto: lo que escribió el usuario.
        disponibles: años que tienen archivos, como texto.

    Returns:
        Tupla (elegidos, no_disponibles): los años pedidos que tienen
        archivos y los que no.
    """
    texto = texto.strip()
    if texto == "":
        return sorted(disponibles), []
    pedidos = []
    for parte in texto.split(","):
        parte = parte.strip()
        if "-" in parte:
            desde, hasta = parte.split("-", 1)
            if desde.strip().isdigit() and hasta.strip().isdigit():
                for anio in range(int(desde), int(hasta) + 1):
                    pedidos.append(str(anio))
        elif parte.isdigit():
            pedidos.append(parte)
    elegidos = sorted(a for a in set(pedidos) if a in disponibles)
    no_disponibles = sorted(a for a in set(pedidos) if a not in disponibles)
    return elegidos, no_disponibles


def interpretar_aglomerados(texto):
    """Convierte lo que escribe el usuario en una lista de aglomerados.

    Acepta códigos separados por comas ('32, 33, 13'). Los ceros iniciales
    se ignoran. Si el texto está vacío, devuelve todos los aglomerados.

    Args:
        texto: lo que escribió el usuario.

    Returns:
        Tupla (validos, invalidos) con los códigos como texto.
    """
    texto = texto.strip()
    if texto == "":
        return list(config.AGLOMERADOS), []
    validos = []
    invalidos = []
    for parte in texto.split(","):
        codigo = parte.strip().lstrip("0")
        if codigo in config.AGLOMERADOS:
            if codigo not in validos:
                validos.append(codigo)
        elif parte.strip() != "":
            invalidos.append(parte.strip())
    return validos, invalidos

        
# esta funcion devuelve el nombre de un aglomerado (o el código si no se conoce)         
def nombre_aglomerado(codigo):
    return config.AGLOMERADOS.get(codigo.lstrip("0"), codigo)
              

def rango_etario(edad, rangos=None):
    """Devuelve el nombre del rango etario al que pertenece una edad.

    Args:
        edad: edad como número (None si no es válida).
        rangos: tuplas (nombre, mínimo, máximo); máximo None = sin límite
            (por defecto config.RANGOS_ETARIOS).

    Returns:
        El nombre del rango o config.RANGO_SIN_EDAD si no entra en ninguno.
    """
    rangos = rangos or config.RANGOS_ETARIOS
    if edad is not None:
        for nombre, minimo, maximo in rangos:
            if edad >= minimo and (maximo is None or edad <= maximo):
                return nombre
    return config.RANGO_SIN_EDAD
 
 
# esta funcion suma una persona (ponderada y sin ponderar) a un grupo
# si el grupo no tiene la clave, la crea; si no tiene el estado, lo crea

def _acumular(grupo, clave, estado, peso):
    """Suma una persona (ponderada y sin ponderar) a un grupo."""
    if clave not in grupo:
        grupo[clave] = {}
    if estado not in grupo[clave]:
        grupo[clave][estado] = {"ponderado": 0, "muestra": 0}
    grupo[clave][estado]["ponderado"] += peso
    grupo[clave][estado]["muestra"] += 1


def contar_tendencias(filas, aglomerados):
    """Cuenta personas por estado en cada aglomerado, ponderadas por PONDERA.

    Solo toma las personas con ESTADO en config.ESTADOS_DISTRIBUCION
    (quedan afuera las entrevistas no realizadas y los menores de 10 años).
    Acepta cualquier iterable de filas, así que se puede usar con
    data_loader.iterar_filas sin cargar el archivo completo.

    Args:
        filas: iterable de diccionarios (una fila por persona).
        aglomerados: códigos de los aglomerados a analizar.

    Returns:
        Diccionario aglomerado -> grupo (total, por_sexo, por_rango_etario)
        -> clave del grupo -> estado -> {ponderado, muestra}. También
        incluye 'sin_pondera': personas descartadas por no tener PONDERA.
    """
    conteos = {}
    for codigo in aglomerados:
        conteos[codigo] = {GRUPO_TOTAL: {}, GRUPO_SEXO: {}, GRUPO_RANGO: {}}
    sin_pondera = 0
    for fila in filas:
        codigo = (fila.get(config.COL_AGLOMERADO) or "").strip().lstrip("0")
        estado = (fila.get(config.COL_ESTADO) or "").strip()
        if codigo not in conteos or estado not in config.ESTADOS_DISTRIBUCION:
            continue
        peso = a_numero(fila.get(config.COL_PONDERA))
        if peso is None:
            sin_pondera += 1
            continue
        sexo = (fila.get(config.COL_SEXO) or "").strip()
        rango = rango_etario(a_numero(fila.get(config.COL_EDAD)))
        grupos = conteos[codigo]
        _acumular(grupos[GRUPO_TOTAL], GRUPO_TOTAL, estado, peso)
        _acumular(grupos[GRUPO_SEXO], config.NOMBRES_SEXO.get(sexo, sexo),
                  estado, peso)
        _acumular(grupos[GRUPO_RANGO], rango, estado, peso)
    return {"aglomerados": conteos, "sin_pondera": sin_pondera}


def sumar_tendencias(lista_conteos):
    """Suma los conteos de varios trimestres (para semestres o años).

    Se suman las personas y no los porcentajes, porque cada trimestre tiene
    una población distinta.

    Args:
        lista_conteos: lista de resultados de contar_tendencias.

    Returns:
        Un diccionario con el mismo formato que contar_tendencias.
    """
    suma = {}
    sin_pondera = 0
    for conteos in lista_conteos:
        sin_pondera += conteos["sin_pondera"]
        for codigo, grupos in conteos["aglomerados"].items():
            if codigo not in suma:
                suma[codigo] = {GRUPO_TOTAL: {}, GRUPO_SEXO: {},
                                GRUPO_RANGO: {}}
            for grupo, claves in grupos.items():
                for clave, estados in claves.items():
                    for estado, valores in estados.items():
                        destino = suma[codigo][grupo]
                        if clave not in destino:
                            destino[clave] = {}
                        if estado not in destino[clave]:
                            destino[clave][estado] = {"ponderado": 0,
                                                      "muestra": 0}
                        destino[clave][estado]["ponderado"] += (
                            valores["ponderado"])
                        destino[clave][estado]["muestra"] += valores["muestra"]
    return {"aglomerados": suma, "sin_pondera": sin_pondera}


def calcular_tasas(estados):
    """Calcula la tasa de desempleo y la distribución de un grupo.

    Población económicamente activa (PEA) = ocupados + desocupados.
    Tasa de desempleo = desocupados / PEA * 100.

    Args:
        estados: diccionario estado -> {ponderado, muestra}.

    Returns:
        Diccionario con la población ponderada de cada estado, la PEA, la
        tasa de desempleo (None si la PEA es 0), el porcentaje de cada
        estado sobre la población y los casos de la muestra.
    """
    ponderados = {}
    muestra = 0
    for estado in config.ESTADOS_DISTRIBUCION:
        valores = estados.get(estado, {"ponderado": 0, "muestra": 0})
        ponderados[estado] = valores["ponderado"]
        muestra += valores["muestra"]
    poblacion = sum(ponderados.values())
    pea = sum(ponderados[e] for e in config.ESTADOS_ACTIVOS)
    desocupados = ponderados[config.ESTADO_DESOCUPADO]
    tasas = {"poblacion": poblacion, "pea": pea}
    for estado in config.ESTADOS_DISTRIBUCION:
        tasas[config.NOMBRES_ESTADO[estado]] = ponderados[estado]
    tasas["tasa_desempleo"] = (
        round(100 * desocupados / pea, 2) if pea else None)
    tasas["distribucion_pct"] = {}
    for estado in config.ESTADOS_DISTRIBUCION:
        nombre = config.NOMBRES_ESTADO[estado]
        tasas["distribucion_pct"][nombre] = (
            round(100 * ponderados[estado] / poblacion, 2)
            if poblacion else None)
    tasas["casos_muestra"] = muestra
    return tasas


def _orden_claves(grupo, claves):
    """Ordena las claves de un grupo: sexo y rango en el orden de config."""
    if grupo == GRUPO_SEXO:
        orden = list(config.NOMBRES_SEXO.values())
    elif grupo == GRUPO_RANGO:
        orden = [r[0] for r in config.RANGOS_ETARIOS] + [config.RANGO_SIN_EDAD]
    else:
        orden = []
    conocidas = [c for c in orden if c in claves]
    return conocidas + sorted(c for c in claves if c not in orden)


def _tasas_de_aglomerado(grupos):
    """Calcula las tasas de cada grupo (total, sexo, rango) de un aglomerado."""
    resultado = {}
    resultado[GRUPO_TOTAL] = calcular_tasas(
        grupos[GRUPO_TOTAL].get(GRUPO_TOTAL, {}))
    for grupo in (GRUPO_SEXO, GRUPO_RANGO):
        resultado[grupo] = {}
        for clave in _orden_claves(grupo, grupos[grupo]):
            resultado[grupo][clave] = calcular_tasas(grupos[grupo][clave])
    return resultado


# esta funcion agrega las tasas de un período a cada aglomerado del informe
# si falta algún aglomerado, se agrega con su nombre y las tasas del período
# si se pasa un diccionario extra, se agrega a cada aglomerado del período
def _agregar_periodo(informe, periodo, conteos, extra=None):
    for codigo, grupos in conteos["aglomerados"].items():
        if codigo not in informe:
            informe[codigo] = {"nombre": nombre_aglomerado(codigo),
                               "periodos": {}}
        informe[codigo]["periodos"][periodo] = _tasas_de_aglomerado(grupos)
        if extra:
            informe[codigo]["periodos"][periodo].update(extra)


# esta funcion arma un informe de tendencias por trimestre
# cada trimestre se calcula con los conteos de ese trimestre
# si falta algún trimestre, se informa igual con los que hay
def armar_informe_trimestral(resultados, metadatos=None):
    """Arma el informe de B.1 con un bloque por trimestre.

    Args:
        resultados: lista de diccionarios con las claves anio, trimestre y
            conteos (resultado de contar_tendencias), uno por archivo.
        metadatos: diccionario con datos del análisis que se copia tal cual.

    Returns:
        Diccionario con metadatos y aglomerados (por código: nombre y
        periodos 'año-trimestre' con las tasas por grupo).
    """
    aglomerados = {}
    for resultado in sorted(resultados,
                            key=lambda r: (r["anio"], r["trimestre"])):
        periodo = resultado["anio"] + "-" + resultado["trimestre"]
        _agregar_periodo(aglomerados, periodo, resultado["conteos"])
    return {"metadatos": metadatos or {}, "aglomerados": aglomerados}


def armar_informe_periodos(resultados, metadatos=None, semestres=None):
    """Arma el informe de B.1 semestral y anual (Modificación 6.5).

    Cada semestre y cada año se calcula sumando los conteos de sus
    trimestres. Si falta algún trimestre, se informa igual con los que hay
    y se indica en 'trimestres_incluidos' y 'completo'.

    Args:
        resultados: lista de diccionarios con las claves anio, trimestre y
            conteos (resultado de contar_tendencias), uno por archivo.
        metadatos: diccionario con datos del análisis que se copia tal cual.
        semestres: semestre -> trimestres (por defecto config.SEMESTRES).

    Returns:
        Diccionario con metadatos, semestral y anual. Cada uno tiene el
        mismo formato que 'aglomerados' en armar_informe_trimestral.
    """
    semestres = semestres or config.SEMESTRES
    por_anio = {}
    for resultado in resultados:
        if resultado["anio"] not in por_anio:
            por_anio[resultado["anio"]] = {}
        por_anio[resultado["anio"]][resultado["trimestre"]] = (
            resultado["conteos"])
    semestral = {}
    anual = {}
    for anio in sorted(por_anio):
        trimestres = por_anio[anio]
        for semestre, incluidos in semestres.items():
            presentes = [t for t in incluidos if t in trimestres]
            if not presentes:
                continue
            suma = sumar_tendencias([trimestres[t] for t in presentes])
            _agregar_periodo(semestral, anio + "-" + semestre, suma, {
                "trimestres_incluidos": presentes,
                "completo": len(presentes) == len(incluidos),
            })
        presentes = sorted(trimestres)
        suma = sumar_tendencias([trimestres[t] for t in presentes])
        _agregar_periodo(anual, anio, suma, {
            "trimestres_incluidos": presentes,
            "completo": len(presentes) == len(config.TRIMESTRES),
        })
    return {"metadatos": metadatos or {}, "semestral": semestral,
            "anual": anual}