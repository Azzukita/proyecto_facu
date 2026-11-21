"""Piezas comunes de la hoja de ayuda (P6).

Cada bloque (A, B, C y D) tiene su módulo ``ayuda_bloque_*.py`` con una
lista de ejemplos. Este módulo define cómo es un ejemplo y cómo se muestra,
así la página trata a los cuatro bloques de la misma manera.
"""
import inspect
from collections import namedtuple

import numpy as np

# Un ejemplo de la hoja de ayuda:
#   tema: uno de los TEMAS de abajo (agrupa los ejemplos en la página).
#   titulo: nombre corto del ejemplo.
#   explicacion: qué muestra y por qué se usó así en el proyecto.
#   funcion: función que calcula el resultado (se muestra su código).
#   entradas: nombres de los datos que recibe, en orden (claves del
#       diccionario que devuelve preparar_datos del bloque).
Ejemplo = namedtuple(
    "Ejemplo", ["tema", "titulo", "explicacion", "funcion", "entradas"])

# Los tres temas que pide la consigna de la hoja de ayuda.
TEMA_AGREGACIONES = "1. Agregaciones simples vs. múltiples"
TEMA_MERGE = "2. Merge"
TEMA_GRAFICO = "3. Estructura para el gráfico"
TEMAS = (TEMA_AGREGACIONES, TEMA_MERGE, TEMA_GRAFICO)


def ejecutar(ejemplo, datos):
    """Ejecuta un ejemplo con los datos preparados de su bloque.

    Args:
        ejemplo: un elemento de la lista EJEMPLOS de un bloque.
        datos: diccionario que devuelve preparar_datos del bloque.

    Returns:
        El DataFrame que devuelve la función del ejemplo.
    """
    return ejemplo.funcion(*[datos[nombre] for nombre in ejemplo.entradas])


def codigo_fuente(ejemplo):
    """Devuelve el código de la función de un ejemplo, para mostrarlo.

    Args:
        ejemplo: un elemento de la lista EJEMPLOS de un bloque.

    Returns:
        El texto del código fuente.
    """
    return inspect.getsource(ejemplo.funcion)


def agrupar_por_tema(ejemplos):
    """Agrupa los ejemplos por tema, en el orden de TEMAS.

    Args:
        ejemplos: lista de Ejemplo.

    Returns:
        Diccionario {tema: lista de ejemplos}; los temas sin ejemplos no
        aparecen.
    """
    grupos = {}
    for tema in TEMAS:
        del_tema = [e for e in ejemplos if e.tema == tema]
        if del_tema:
            grupos[tema] = del_tema
    return grupos


def tablas_iguales(a, b, tolerancia=0.11):
    """Compara dos DataFrames numéricos con la misma forma.

    Sirve para comprobar que groupby + unstack y pivot_table dan lo mismo.
    Ignora el orden de las columnas y el nombre de los índices; tolera
    diferencias de redondeo.

    Args:
        a: primer DataFrame.
        b: segundo DataFrame.
        tolerancia: diferencia máxima aceptada entre valores.

    Returns:
        True si tienen el mismo índice, las mismas columnas y valores
        iguales dentro de la tolerancia.
    """
    if set(a.columns) != set(b.columns) or not a.index.equals(b.index):
        return False
    b = b[list(a.columns)]
    return bool(np.allclose(a.to_numpy(), b.to_numpy(), atol=tolerancia,
                            equal_nan=True))