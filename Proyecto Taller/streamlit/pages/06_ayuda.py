"""Página 06: hoja de ayuda con ejemplos de pandas de los cuatro bloques.

Cada bloque tiene su módulo ``src/ayuda_bloque_*.py`` con ejemplos que
trabajan con los datos reales. La página muestra el código de cada ejemplo
y, al apretar el botón de la pestaña, su resultado. No hay lógica de
cálculo acá: todo se calcula en esos módulos.
"""
import streamlit as st

from src import ayuda_bloque_a as bloque_a
from src import ayuda_bloque_b as bloque_b
from src import ayuda_bloque_c as bloque_c
from src import ayuda_bloque_d as bloque_d
from src import ayuda_comun, data_loader
from src import hogares_tecnologia as ht
from src import mercado_laboral as ml

# Descripción del panel del Bloque A (src/panel_calidad.py).
FUNCIONES_A = [
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

EJEMPLO_GROUPBY_A = """\
df_rol.groupby("Etiqueta")["Porcentaje Faltantes (%)"].mean().reset_index()
"""

EJEMPLO_GRAFICO_A = """\
st.bar_chart(
    df_rol,
    x="Columna",
    y=["Porcentaje Válidos (%)",
       "Porcentaje Faltantes (%)",
       "Porcentaje No Corresponde (%)"],
    horizontal=True,
)
"""


@st.cache_data(show_spinner="Leyendo los informes de calidad...")
def datos_bloque_a():
    """Prepara (una sola vez) los datos de los ejemplos del Bloque A."""
    return bloque_a.preparar_datos()


@st.cache_data(show_spinner="Leyendo los archivos de individuos...")
def individuos():
    """Carga (una sola vez) los individuos, que usan los Bloques B y D."""
    return ml.cargar_datos_individuos()


@st.cache_data(show_spinner="Leyendo los archivos de hogares...")
def datos_bloque_c(anio):
    """Prepara (una sola vez por año) los datos del Bloque C."""
    return bloque_c.preparar_datos(anio)


def datos_bloque_b():
    """Prepara los datos de los ejemplos del Bloque B."""
    return bloque_b.preparar_datos(individuos())


@st.cache_data(show_spinner="Armando los datos del mapa...")
def datos_bloque_d():
    """Prepara (una sola vez) los datos de los ejemplos del Bloque D."""
    return bloque_d.preparar_datos(individuos())


def mostrar_ejemplos(clave, modulo, cargar):
    """Muestra los ejemplos de un bloque, agrupados por tema.

    El código de cada ejemplo se ve siempre; el resultado aparece cuando
    se aprieta el botón, para no cargar todos los datos al abrir la
    página.

    Args:
        clave: texto corto que identifica al bloque (para los botones).
        modulo: módulo ``ayuda_bloque_*`` del bloque.
        cargar: función sin argumentos que devuelve los datos preparados.
    """
    st.markdown(modulo.RESUMEN)
    if st.button("Ejecutar ejemplos", key=f"ayuda_ejecutar_{clave}"):
        st.session_state[f"ayuda_listo_{clave}"] = True
    datos = None
    if st.session_state.get(f"ayuda_listo_{clave}"):
        try:
            datos = cargar()
        except FileNotFoundError as error:
            st.warning(str(error))
    else:
        st.caption("Apretá el botón para cargar los datos y ver los "
                   "resultados de cada ejemplo.")
    for tema, ejemplos in ayuda_comun.agrupar_por_tema(
            modulo.EJEMPLOS).items():
        st.subheader(tema)
        for ejemplo in ejemplos:
            st.markdown(f"**{ejemplo.titulo}**")
            st.markdown(ejemplo.explicacion)
            st.code(ayuda_comun.codigo_fuente(ejemplo), language="python")
            if datos is not None:
                st.dataframe(ayuda_comun.ejecutar(ejemplo, datos))
    if datos is not None:
        igual = "sí" if modulo.son_equivalentes(datos) else "no"
        st.caption("¿`groupby` + `unstack` y `pivot_table` dan el mismo "
                   f"resultado con estos datos? {igual}.")


def mostrar_funciones_a():
    """Muestra la tabla de funciones de `src/panel_calidad.py`."""
    filas = ["| Función | Qué hace |", "|---|---|"]
    for nombre, descripcion in FUNCIONES_A:
        filas.append(f"| `{nombre}` | {descripcion} |")
    st.markdown("\n".join(filas))


def mostrar_lo_que_usa_el_panel():
    """Explica cómo resuelve el panel del Bloque A cada tema de pandas."""
    st.markdown("**1. Agregaciones.** El panel usa una agregación simple: "
                "una columna y una función.")
    st.code(EJEMPLO_GROUPBY_A, language="python")
    st.markdown(
        "- `groupby(\"Etiqueta\")` agrupa las filas por etiqueta.\n"
        "- `[\"Porcentaje Faltantes (%)\"].mean()` calcula el promedio de "
        "esa columna en cada grupo.\n"
        "- `reset_index()` devuelve un DataFrame común, que la página "
        "recorre con `iterrows()` para mostrar una métrica por etiqueta.\n"
        "- El conteo de registros afectados (`contar_por_etiqueta`) no "
        "usa `sum()` de pandas: suma con un bucle sobre un diccionario y "
        "después arma el DataFrame con `pd.DataFrame`."
    )
    st.markdown("**2. Merge.** El panel no usa `merge`: trabaja con "
                "informes JSON ya generados, no con datasets que haya que "
                "cruzar.")
    st.markdown(
        "**3. Estructura del gráfico.** El panel no usa `pivot_table()` "
        "ni `groupby()` + `unstack()`: `armar_tabla_faltantes` construye "
        "una lista de diccionarios (uno por columna) y la convierte con "
        "`pd.DataFrame`. La tabla ya sale en formato ancho, una columna "
        "por métrica, y `st.bar_chart` la grafica directo:")
    st.code(EJEMPLO_GRAFICO_A, language="python")


def mostrar_uso_del_panel():
    """Describe paso a paso cómo se usa el panel de control."""
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
st.caption("Ejemplos de pandas de cada bloque, con los datos del proyecto")
st.info(
    "**Regla de diseño:** las páginas no tienen lógica de cálculo suelta. "
    "Solo llaman a funciones de `src/`, donde está todo el trabajo con "
    "pandas. Acá se muestran tres temas: agregaciones simples vs. "
    "múltiples, `merge` y la estructura de las tablas para los gráficos "
    "(`groupby` + `unstack` vs. `pivot_table`). Cada ejemplo es una "
    "función real: el código que se ve es el que se ejecuta."
)

tab_a, tab_b, tab_c, tab_d = st.tabs([
    "Bloque A · Calidad de datos",
    "Bloque B · Mercado laboral",
    "Bloque C · Hogares y tecnología",
    "Bloque D · Mapas",
])

with tab_a:
    st.caption("Panel de Control de Completitud y Calidad de Datos "
               "(página Carga y Estado)")
    with st.expander("Cómo se usa el panel"):
        mostrar_uso_del_panel()
    with st.expander("Funciones de src/panel_calidad.py"):
        mostrar_funciones_a()
    with st.expander("Qué pandas usa el panel hoy"):
        mostrar_lo_que_usa_el_panel()
    mostrar_ejemplos("a", bloque_a, datos_bloque_a)

with tab_b:
    st.caption("Evolución y brechas del mercado laboral (página Mercado "
               "Laboral y Género)")
    mostrar_ejemplos("b", bloque_b, datos_bloque_b)

with tab_c:
    st.caption("Tecnología y condiciones de habitabilidad (página Hogares "
               "y Tecnología)")
    anios_c = ht.anios_disponibles_cruce(data_loader.escanear_datos())
    if anios_c:
        anio_c = st.selectbox("Año de los ejemplos", anios_c,
                              index=len(anios_c) - 1, key="ayuda_anio_c")
        mostrar_ejemplos("c", bloque_c, lambda: datos_bloque_c(anio_c))
    else:
        st.warning("No hay archivos de Ciencia y Tecnología con hogares "
                   "de Mercado Laboral para el mismo año.")

with tab_d:
    st.caption("Mapa georreferenciado (página Mapa)")
    mostrar_ejemplos("d", bloque_d, datos_bloque_d)