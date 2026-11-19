import json
import pandas as pd

from src import config

def listar_informes():
    """Busca y retorna los archivos JSON de calidad datos en la carpeta de salida."""
    return sorted(config.DIR_SALIDA.glob("calidad_datos*.json"))


def cargar_todos_los_informes():
    """Carga todos los informes JSON encontrados en un diccionario."""
    informes = {}
    for ruta in listar_informes():
        with open(ruta, "r", encoding="utf-8") as f:
            informes[ruta.name] = json.load(f)
    return informes


def extraer_datos_completitud(informe_activo):
    """Navega de forma segura por el JSON para encontrar el bloque de completitud.

    El bloque de completitud se reconoce porque cada trimestre tiene la clave
    "columnas". Así no se confunde con el bloque de inconsistencias, que
    también tiene "por_trimestre" pero tiene "reglas" en vez de "columnas".
    """
    datos_completitud = {}

    for valor in informe_activo.values():
        if isinstance(valor, dict) and "por_trimestre" in valor:
            primer_trimestre = next(iter(valor["por_trimestre"].values()), {})
            if "columnas" in primer_trimestre:
                datos_completitud = valor
                break

    if not datos_completitud and isinstance(informe_activo, dict):
        datos_completitud = informe_activo

    return datos_completitud


def armar_tabla_faltantes(columnas_dict, columnas_del_rol, etiquetas_seleccionadas):
    """Arma la tabla de faltantes de un trimestre, filtrada por rol y etiqueta."""
    datos_grafico = []

    for nombre_columna, datos_col in columnas_dict.items():
        pct_faltantes = datos_col.get("pct_faltantes", 0.0)
        supera_umbral = datos_col.get("supera_umbral", False)
        faltantes_reales = datos_col.get("faltantes_reales", 0)

        etiqueta = "Supera umbral" if supera_umbral else "No supera umbral"

        if etiqueta not in etiquetas_seleccionadas:
            continue

        if columnas_del_rol and nombre_columna not in columnas_del_rol:
            continue

        datos_grafico.append({
            "Columna": nombre_columna,
            "Etiqueta": etiqueta,
            "Faltantes Reales": faltantes_reales,
            "Porcentaje Faltantes (%)": pct_faltantes,
            "Porcentaje Válidos (%)": datos_col.get("pct_validos", 0.0),
            "Porcentaje No Corresponde (%)": datos_col.get("pct_no_corresponde", 0.0),
            "Supera Umbral": "Sí" if supera_umbral else "No"
        })

    return pd.DataFrame(datos_grafico)


def promedio_por_etiqueta(df_rol):
    """Calcula el promedio del porcentaje de faltantes de cada etiqueta."""
    return df_rol.groupby("Etiqueta")["Porcentaje Faltantes (%)"].mean().reset_index()


def columnas_sin_datos(columnas_dict, columnas_del_rol):
    """Devuelve las columnas del rol que no están en el informe elegido."""
    return [columna for columna in columnas_del_rol if columna not in columnas_dict]


def extraer_datos_consistencia(informe_activo):
    """Busca en el JSON el bloque de inconsistencias (trimestres con "reglas")."""
    for valor in informe_activo.values():
        if isinstance(valor, dict) and "por_trimestre" in valor:
            primer_trimestre = next(iter(valor["por_trimestre"].values()), {})
            if "reglas" in primer_trimestre:
                return valor
    return {}


def reglas_del_rol(reglas_dict, columnas_del_rol, etiquetas):
    """Devuelve las reglas con alguna de las etiquetas elegidas que usan
    alguna columna del rol."""
    elegidas = {}
    for nombre, datos in reglas_dict.items():
        if datos["etiqueta"] not in etiquetas:
            continue
        if not set(datos["columnas"]) & set(columnas_del_rol):
            continue
        elegidas[nombre] = datos
    return elegidas


def contar_por_etiqueta(reglas_dict, columnas_del_rol, etiquetas):
    """Suma la cantidad de registros afectados de cada etiqueta."""
    conteo = {etiqueta: 0 for etiqueta in etiquetas}
    for datos in reglas_del_rol(reglas_dict, columnas_del_rol, etiquetas).values():
        conteo[datos["etiqueta"]] += datos["cantidad"]
    return pd.DataFrame({
        "Etiqueta": list(conteo.keys()),
        "Registros Afectados": list(conteo.values())
    })


def tabla_registros(reglas_dict, columnas_del_rol, etiquetas):
    """Arma la tabla con los registros (ejemplos del JSON) que
    presentan las inconsistencias de las etiquetas elegidas."""
    filas = []
    for nombre, datos in reglas_del_rol(reglas_dict, columnas_del_rol, etiquetas).items():
        for ejemplo in datos.get("ejemplos", []):
            fila = {"Etiqueta": datos["etiqueta"], "Regla": nombre}
            fila.update(ejemplo)
            filas.append(fila)
    return pd.DataFrame(filas)


def informes_de_faltantes(diccionario_informes):
    """Devuelve solo los informes que tienen datos de faltantes."""
    elegidos = {}
    for nombre, informe in diccionario_informes.items():
        if "por_trimestre" in extraer_datos_completitud(informe):
            elegidos[nombre] = informe
    return elegidos


def informes_de_consistencia(diccionario_informes):
    """Devuelve solo los informes que tienen datos de inconsistencias."""
    elegidos = {}
    for nombre, informe in diccionario_informes.items():
        if extraer_datos_consistencia(informe):
            elegidos[nombre] = informe
    return elegidos

