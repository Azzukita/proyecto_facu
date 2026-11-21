"""Página 06: hoja de ayuda sobre el uso de pandas en el Bloque A."""

import streamlit as st

FUNCIONES = [
    ("cargar_todos_los_informes",
     "Lee los `calidad_datos*.json` de la carpeta de salida y los guarda "
     "en un diccionario (nombre de archivo -> contenido)."),
    ("extraer_datos_completitud",
     "Busca el bloque de completitud del JSON (trimestres con la clave "
     "`columnas`)."),
    ("extraer_datos_consistencia",
     "Busca el bloque de inconsistencias (trimestres con la clave "
     "`reglas`)."),
    ("armar_tabla_faltantes",
     "Arma el DataFrame de faltantes de un trimestre, filtrado por rol y "
     "por etiqueta."),
    ("promedio_por_etiqueta",
     "Promedio de faltantes por etiqueta con `groupby`."),
    ("contar_por_etiqueta",
     "Suma los registros afectados por etiqueta."),
    ("tabla_registros",
     "Arma la tabla con los registros (ejemplos del JSON) de las "
     "inconsistencias."),
    ("reglas_del_rol",
     "Selecciona las reglas según las etiquetas y las columnas del rol."),
    ("columnas_sin_datos",
     "Columnas del rol que no están en el informe."),
    ("informes_de_faltantes / informes_de_consistencia",
     "Separan los informes según el tipo de datos que tienen."),
]

EJEMPLO_GROUPBY = """\
df_rol.groupby("Etiqueta")["Porcentaje Faltantes (%)"].mean().reset_index()
"""

EJEMPLO_GRAFICO = """\
st.bar_chart(
    df_rol,
    x="Columna",
    y=["Porcentaje Válidos (%)",
       "Porcentaje Faltantes (%)",
       "Porcentaje No Corresponde (%)"],
    horizontal=True,
)
"""


def mostrar_funciones():
    """Muestra la tabla de funciones de `src/panel_calidad.py`."""
    st.subheader("Funciones de src/panel_calidad.py")
    filas = ["| Función | Qué hace |", "|---|---|"]
    for nombre, descripcion in FUNCIONES:
        filas.append(f"| `{nombre}` | {descripcion} |")
    st.markdown("\n".join(filas))


def mostrar_agregaciones():
    """Explica las agregaciones simples y múltiples del Bloque A."""
    st.subheader("1. Agregaciones simples vs. múltiples")
    st.markdown("Se usa una **agregación simple**: una columna y una función.")
    st.code(EJEMPLO_GROUPBY, language="python")
    st.markdown(
        "- `groupby(\"Etiqueta\")` agrupa las filas por etiqueta.\n"
        "- `[\"Porcentaje Faltantes (%)\"].mean()` calcula el promedio de "
        "esa columna en cada grupo.\n"
        "- `reset_index()` devuelve un DataFrame común, que la página "
        "recorre con `iterrows()` para mostrar una métrica por etiqueta."
    )
    st.markdown(
        "El conteo de registros afectados (`contar_por_etiqueta`) no usa "
        "`sum()` de pandas: suma con un bucle sobre un diccionario y "
        "después arma el DataFrame con `pd.DataFrame`."
    )
    st.info("En el Bloque A no se usa `agg()`.")


def mostrar_merge():
    """Aclara que el Bloque A no usa merge."""
    st.subheader("2. Merge")
    st.info(
        "El Bloque A no usa `merge`. El panel trabaja con informes JSON ya "
        "generados, no con datasets que haya que cruzar."
    )


def mostrar_estructura_grafico():
    """Explica cómo se estructura la tabla que alimenta los gráficos."""
    st.subheader("3. Estructura para el gráfico")
    st.info("No se usa `pivot_table()` ni `groupby()` + `unstack()`.")
    st.markdown(
        "- `armar_tabla_faltantes` construye una lista de diccionarios "
        "(uno por columna) y la convierte con "
        "`pd.DataFrame(datos_grafico)`. La tabla ya sale en formato "
        "ancho: una columna por métrica (Porcentaje Válidos, Faltantes y "
        "No Corresponde).\n"
        "- Por eso `st.bar_chart` la grafica directo:"
    )
    st.code(EJEMPLO_GRAFICO, language="python")
    st.markdown(
        "- El gráfico de inconsistencias usa `df_conteo` (columnas "
        "`Etiqueta` y `Registros Afectados`), también sin reestructurar."
    )


def mostrar_uso_del_panel():
    """Describe paso a paso cómo se usa el panel de control."""
    st.subheader("Cómo se usa el panel")
    st.markdown(
        "1. **Elegir el rol.** Define las columnas que se analizan "
        "(`config.ROLES`).\n"
        "2. **Opcional:** excluir registros CRÍTICO. El estado queda en "
        "`session_state`.\n"
        "3. **Pestaña Faltantes:** elegir reporte, trimestre y estado de "
        "completitud. Muestra métricas, gráfico y tabla detallada.\n"
        "4. **Pestaña Inconsistencias:** elegir reporte, trimestre y "
        "etiquetas. Muestra el gráfico de registros afectados y la tabla "
        "por etiqueta."
    )


st.title("Hoja de ayuda")
st.caption("Pandas en el Bloque A: Panel de Control de Completitud y "
           "Calidad de Datos")

st.info(
    "**Regla de diseño:** la página `02_carga_y_estado.py` no tiene "
    "lógica de cálculo suelta. Solo llama a funciones de "
    "`src/panel_calidad.py`, donde está todo el trabajo con pandas."
)

tab_uso, tab_funciones, tab_agg, tab_merge, tab_grafico = st.tabs([
    "Cómo se usa",
    "Funciones",
    "1. Agregaciones",
    "2. Merge",
    "3. Gráfico",
])

with tab_uso:
    mostrar_uso_del_panel()

with tab_funciones:
    mostrar_funciones()

with tab_agg:
    mostrar_agregaciones()

with tab_merge:
    mostrar_merge()

with tab_grafico:
    mostrar_estructura_grafico()
    