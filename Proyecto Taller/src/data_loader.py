"""Lectura y detección automática de los archivos de la EPH."""
import csv
import json
from datetime import datetime
from pathlib import Path

from src import config


def _abrir(ruta, encoding):
    """Abre un archivo de texto para leerlo, con mensajes de error claros.

    Args:
        ruta: ruta al archivo.
        encoding: codificación con la que se abre.

    Returns:
        El archivo abierto (se usa con 'with').

    Raises:
        FileNotFoundError: si el archivo no existe.
        PermissionError: si no se tiene permiso para leerlo.
    """
    try:
        return open(Path(ruta), encoding=encoding, newline="")
    except FileNotFoundError:
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")
    except PermissionError:
        raise PermissionError(f"No hay permiso para leer el archivo: {ruta}")


def leer_filas(ruta, delimitador=None, encoding=None):
    """Lee un archivo CSV de la EPH y devuelve una lista de diccionarios.

    Carga el archivo completo en memoria. Para recorrerlo una sola vez
    conviene iterar_filas. Si el archivo no se puede decodificar con la
    codificación indicada, se prueban las de config.ENCODINGS_ALTERNATIVOS.

    Args:
        ruta: ruta al archivo.
        delimitador: separador de columnas (por defecto config.SEPARADOR).
        encoding: codificación (por defecto config.ENCODING).

    Returns:
        Lista de diccionarios, uno por fila. Todos los valores son texto.

    Raises:
        FileNotFoundError: si el archivo no existe.
        ValueError: si no se pudo decodificar o no tiene formato CSV.
    """
    delimitador = delimitador or config.SEPARADOR
    codificaciones = [encoding or config.ENCODING]
    codificaciones.extend(config.ENCODINGS_ALTERNATIVOS)
    for codificacion in codificaciones:
        try:
            with _abrir(ruta, codificacion) as archivo:
                return list(csv.DictReader(archivo, delimiter=delimitador))
        except UnicodeDecodeError:
            continue
        except csv.Error as error:
            raise ValueError(f"{ruta} no tiene formato CSV válido: {error}")
    raise ValueError(
        f"No se pudo leer {ruta} con las codificaciones {codificaciones}")


def iterar_filas(ruta, delimitador=None, encoding=None):
    """Lee un archivo CSV de la EPH una fila por vez (generador).

    A diferencia de leer_filas, no carga el archivo completo en memoria:
    sirve para recorrer archivos grandes una sola vez. Los errores (por
    ejemplo, un archivo que no existe) aparecen al empezar a recorrerlo.

    Args:
        ruta: ruta al archivo.
        delimitador: separador de columnas (por defecto config.SEPARADOR).
        encoding: codificación (por defecto config.ENCODING).

    Yields:
        Un diccionario por fila.
    """
    delimitador = delimitador or config.SEPARADOR
    encoding = encoding or config.ENCODING
    with _abrir(ruta, encoding) as archivo:
        try:
            yield from csv.DictReader(archivo, delimiter=delimitador)
        except csv.Error as error:
            raise ValueError(f"{ruta} no tiene formato CSV válido: {error}")


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
    with _abrir(ruta, encoding) as archivo:
        lector = csv.reader(archivo, delimiter=delimitador)
        for fila in lector:
            return fila
    return []


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

    Raises:
        FileNotFoundError: si la carpeta de datos no existe.
    """
    directorio = Path(directorio or config.DIR_DATOS)
    if not directorio.is_dir():
        raise FileNotFoundError(
            f"No se encontró la carpeta de datos: {directorio}. "
            "Debe llamarse 'files' y estar al lado de la carpeta del "
            "proyecto (se configura en config.DIR_DATOS).")
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


def listar_categorias(directorio=None):
    """Devuelve las categorías que hay en la carpeta de datos.

    Cada carpeta directamente dentro de la carpeta de datos es una
    categoría. Las carpetas ocultas (que empiezan con '.') se ignoran.

    Args:
        directorio: carpeta raíz de datos (por defecto config.DIR_DATOS).

    Returns:
        Lista de nombres de categoría, ordenada. Vacía si la carpeta de
        datos no existe.
    """
    directorio = Path(directorio or config.DIR_DATOS)
    if not directorio.is_dir():
        return []
    return sorted(
        ruta.name for ruta in directorio.iterdir()
        if ruta.is_dir() and not ruta.name.startswith(".")
    )


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


def _escribir_json(datos, ruta):
    """Escribe datos en un archivo JSON.

    Primero se convierte todo a texto y recién después se abre el archivo,
    así un dato que no se puede guardar no deja un archivo a medias.

    Args:
        datos: contenido serializable a JSON.
        ruta: archivo de destino.

    Raises:
        TypeError: si los datos no se pueden convertir a JSON.
        OSError: si no se puede escribir el archivo.
    """
    texto = json.dumps(datos, ensure_ascii=False, indent=2)
    try:
        with open(ruta, "w", encoding=config.ENCODING) as archivo:
            archivo.write(texto)
    except OSError as error:
        raise OSError(f"No se pudo escribir {ruta}: {error}")


def guardar_reporte(seccion, datos, ruta=None):
    """Agrega o reemplaza una sección del reporte JSON sin pisar el resto.

    Si la carpeta del archivo no existe, la crea. Si el archivo existente
    está dañado (no es un JSON válido), lo conserva con el sufijo
    '_danado' y empieza uno nuevo.

    Args:
        seccion: nombre de la sección, por ejemplo 'completitud_hogares'.
        datos: contenido serializable a JSON.
        ruta: archivo de reporte (por defecto config.RUTA_REPORTE).
    """
    ruta = Path(ruta or config.RUTA_REPORTE)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    reporte = {}
    if ruta.exists():
        try:
            with open(ruta, encoding=config.ENCODING) as archivo:
                reporte = json.load(archivo)
        except json.JSONDecodeError:
            copia = ruta.with_name(ruta.stem + "_danado" + ruta.suffix)
            ruta.replace(copia)
            print(f"AVISO: {ruta.name} estaba dañado. Se conservó como "
                  f"{copia.name} y se crea uno nuevo.")
    reporte[seccion] = datos
    _escribir_json(reporte, ruta)


def guardar_json(datos, ruta, si_existe=None):
    """Guarda un informe en un archivo JSON controlando si ya existe.

    Args:
        datos: contenido serializable a JSON.
        ruta: archivo de destino.
        si_existe: qué hacer si el archivo ya existe: 'preguntar' (pregunta
            si se sobrescribe) o 'timestamp' (guarda uno nuevo con fecha y
            hora). Por defecto config.MODO_ARCHIVO_EXISTENTE.

    Returns:
        La ruta donde se guardó, o None si el usuario decidió no guardar.

    Raises:
        ValueError: si 'si_existe' no es una opción válida.
    """
    si_existe = si_existe or config.MODO_ARCHIVO_EXISTENTE
    if si_existe not in ("preguntar", "timestamp"):
        raise ValueError("si_existe debe ser 'preguntar' o 'timestamp'")
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.exists():
        if si_existe == "preguntar":
            try:
                respuesta = input(
                    f"{ruta.name} ya existe. ¿Sobrescribir? (s/n): ")
            except (EOFError, RuntimeError):
                # No hay teclado disponible: no se pisa nada.
                print("No se puede preguntar en este entorno: "
                      "se guarda con fecha y hora.")
                respuesta = "n"
                si_existe = "timestamp"
            else:
                if respuesta.strip().lower() != "s":
                    print("No se guardó el informe.")
                    return None
        if si_existe == "timestamp":
            marca = datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta = ruta.with_name(f"{ruta.stem}_{marca}{ruta.suffix}")
    _escribir_json(datos, ruta)
    return ruta
