"""Lectura y detección automática de los archivos de la EPH."""
import csv
import json
from pathlib import Path
 
from src import config
 
# Tengo dudas de si no va a terminar tardando mucho,
# tendriamos que que conviene despues de probarlo bien.
# Recordar que esto lee un archivo completo
# y devuelve una lista de diccionarios (una por fila).
def leer_filas(ruta, delimitador=None, encoding=None):
    """Lee un archivo CSV de la EPH y devuelve una lista de diccionarios.
 
    Carga el archivo completo en memoria. Para recorrerlo una sola vez
    conviene iterar_filas.
 
    Args:
        ruta: ruta al archivo.
        delimitador: separador de columnas (por defecto config.SEPARADOR).
        encoding: codificación (por defecto config.ENCODING).
 
    Returns:
        Lista de diccionarios, uno por fila. Todos los valores son texto.
    """
    delimitador = delimitador or config.SEPARADOR
    encoding = encoding or config.ENCODING
    with open(Path(ruta), encoding=encoding, newline="") as archivo:
        lector = csv.DictReader(archivo, delimiter=delimitador)
        return list(lector)


def iterar_filas(ruta, delimitador=None, encoding=None):
    """Lee un archivo CSV de la EPH una fila por vez (generador).
 
    A diferencia de leer_filas, no carga el archivo completo en memoria:
    sirve para recorrer archivos grandes una sola vez.
 
    Args:
        ruta: ruta al archivo.
        delimitador: separador de columnas (por defecto config.SEPARADOR).
        encoding: codificación (por defecto config.ENCODING).
 
    Yields:
        Un diccionario por fila.
    """
    delimitador = delimitador or config.SEPARADOR
    encoding = encoding or config.ENCODING
    with open(Path(ruta), encoding=encoding, newline="") as archivo:
        yield from csv.DictReader(archivo, delimiter=delimitador)


# devuelve solo los nombres de las columnas.
def leer_columnas(ruta, delimitador=None, encoding=None):
    """Devuelve los nombres de las columnas leyendo solo el encabezado.
 
    Args:
        ruta: ruta al archivo.
        delimitador: separador de columnas (por defecto config.SEPARADOR).
        encoding: codificación (por defecto config.ENCODING).
 
    Returns:
        Lista con los nombres de las columnas, en orden. Lista vacía si
        el archivo está vacío.
    """
    delimitador = delimitador or config.SEPARADOR
    encoding = encoding or config.ENCODING
    with open(Path(ruta), encoding=encoding, newline="") as archivo:
        lector = csv.reader(archivo, delimiter=delimitador)
        for fila in lector:
            return fila
    return []


# dice si un nombre de archivo es de hogar o de individuo, o None.
def tipo_de_archivo(nombre):
    """Indica si un archivo es de hogares o de individuos según su nombre.
 
    Args:
        nombre: nombre del archivo, por ejemplo 'usu_hogar_T124.txt'.
 
    Returns:
        El tipo (config.TIPO_HOGAR o config.TIPO_INDIVIDUO) o None si el
        nombre no contiene ninguna de las palabras clave.
    """
    nombre = nombre.lower()
    for tipo, claves in config.CLAVES_TIPO.items():
        for clave in claves:
            if clave in nombre:
                return tipo
    return None


#saca (año, trimestre) del final del nombre, o None
def periodo_de_archivo(nombre):
    """Obtiene el año y el trimestre a partir del final del nombre.
 
    Se espera que el nombre termine en una 't' seguida de tres dígitos
    (trimestre de 1 a 4 y año de dos cifras) y la extensión '.txt'. Por
    ejemplo, 'usu_hogar_T124.txt' corresponde al trimestre 1 de 2024.
    Se supone que todos los años son 20xx.
 
    Args:
        nombre: nombre del archivo.
 
    Returns:
        Tupla (año, trimestre) como texto, por ejemplo ('2024', 'T1'),
        o None si el nombre no sigue ese formato.
    """
    if not nombre.lower().endswith(".txt"):
        return None
    texto = nombre[:-4]
    if len(texto) < 4 or texto[-4].lower() != "t":
        return None
    final = texto[-3:]
    if not final.isdigit() or final[0] not in "1234":
        return None
    return "20" + final[1:], "T" + final[0]


# recorre data/ y arma el inventario de archivos reconocidos
def escanear_datos(directorio=None):
    """Detecta los archivos de la EPH disponibles dentro de una carpeta.
 
    La primera subcarpeta es la categoría. Se busca en cualquier nivel de
    subcarpetas, para respetar cómo se descomprimieron los archivos. Los
    archivos cuyo nombre no permite deducir el tipo o el período se ignoran.
 
    Args:
        directorio: carpeta raíz donde buscar (por defecto config.DIR_DATOS).
 
    Returns:
        Lista de diccionarios con las claves: categoria, anio, trimestre,
        tipo y ruta.
    """
    directorio = Path(directorio or config.DIR_DATOS)
    encontrados = []
    for ruta in sorted(directorio.rglob("*.txt")):
        partes = ruta.relative_to(directorio).parts
        tipo = tipo_de_archivo(ruta.name)
        periodo = periodo_de_archivo(ruta.name)
        if len(partes) < 2 or tipo is None or periodo is None:
            continue
        encontrados.append({
            "categoria": partes[0],
            "anio": periodo[0],
            "trimestre": periodo[1],
            "tipo": tipo,
            "ruta": ruta,
        })
    return encontrados


def filtrar_archivos(archivos, tipo=None, categoria=None, anios=None,
                     trimestres=None):
    """Filtra una lista de archivos ya detectados. Cada filtro es opcional.
 
    Args:
        archivos: lista de diccionarios devuelta por escanear_datos.
        tipo: config.TIPO_HOGAR o config.TIPO_INDIVIDUO (None = ambos).
        categoria: carpeta de categoría (None = todas).
        anios: lista de años como texto, por ejemplo ['2024'] (None = todos).
        trimestres: lista de trimestres, por ejemplo ['T1'] (None = todos).
 
    Returns:
        Lista filtrada, ordenada por año y trimestre.
    """
    elegidos = []
    for archivo in archivos:
        if tipo is not None and archivo["tipo"] != tipo:
            continue
        if categoria is not None and archivo["categoria"] != categoria:
            continue
        if anios is not None and archivo["anio"] not in anios:
            continue
        if trimestres is not None and archivo["trimestre"] not in trimestres:
            continue
        elegidos.append(archivo)
    return sorted(elegidos, key=lambda a: (a["anio"], a["trimestre"]))


# escanea y filtra lo que hacen las funciones escanear_archivos
# y filtrar_archivos
def buscar_archivos(tipo=None, categoria=None, anios=None, trimestres=None,
                    directorio=None):
    """Detecta los archivos de una carpeta y los filtra en un solo paso.
 
    Es escanear_datos seguido de filtrar_archivos. Sin filtros devuelve todo
    lo que haya en la carpeta, así que agregar años, trimestres o categorías
    nuevas no requiere tocar el código.
 
    Args:
        tipo: config.TIPO_HOGAR o config.TIPO_INDIVIDUO (None = ambos).
        categoria: carpeta de categoría (None = todas).
        anios: lista de años como texto (None = todos).
        trimestres: lista de trimestres (None = todos).
        directorio: carpeta raíz donde buscar (por defecto config.DIR_DATOS).
 
    Returns:
        Lista de diccionarios (ver escanear_datos), ordenada por año y
        trimestre.
    """
    archivos = escanear_datos(directorio)
    return filtrar_archivos(archivos, tipo, categoria, anios, trimestres)


# para cada trimestre esperado revisa
# que existan el archivo de hogar y el de individuo.
# Si llegara a faltar alguno de los dos, 
# agrega ese trimestre a la lista y va al siguiente.
def trimestres_faltantes(archivos, categoria, anio, esperados=None):
    """Indica qué trimestres de un año no tienen hogar e individuo.
 
    Para cada trimestre esperado revisa que existan el archivo de hogar y el
    de individuo. Si falta alguno de los dos, agrega ese trimestre a la
    lista y sigue con el siguiente.
 
    Args:
        archivos: lista de diccionarios devuelta por escanear_datos.
        categoria: categoría a revisar.
        anio: año como texto.
        esperados: trimestres que debería haber (por defecto
            config.TRIMESTRES).
 
    Returns:
        Lista de trimestres faltantes; vacía si el año está completo.
    """
    esperados = esperados or config.TRIMESTRES
    faltan = []
    for trimestre in esperados:
        for tipo in (config.TIPO_HOGAR, config.TIPO_INDIVIDUO):
            candidatos = filtrar_archivos(
                archivos,
                tipo=tipo,
                categoria=categoria,
                anios=[str(anio)],
                trimestres=[trimestre],
            )
            if not candidatos:
                faltan.append(trimestre)
                break
    return faltan


# gaurda en un archivo JSON el reporta
def guardar_reporte(seccion, datos, ruta=None):
    """Agrega o reemplaza una sección del reporte JSON sin pisar el resto.
 
    Si la carpeta del archivo no existe, la crea.
 
    Args:
        seccion: nombre de la sección, por ejemplo 'completitud_hogares'.
        datos: contenido serializable a JSON.
        ruta: archivo de reporte (por defecto config.RUTA_REPORTE).
    """
    ruta = Path(ruta or config.RUTA_REPORTE)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    reporte = {}
    if ruta.exists():
        with open(ruta, encoding=config.ENCODING) as archivo:
            reporte = json.load(archivo)
    reporte[seccion] = datos
    with open(ruta, "w", encoding=config.ENCODING) as archivo:
        json.dump(reporte, archivo, ensure_ascii=False, indent=2)