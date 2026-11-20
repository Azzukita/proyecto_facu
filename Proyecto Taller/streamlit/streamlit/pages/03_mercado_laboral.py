"""Página P3: Mercado Laboral y Género (Bloque B).

La página solo arma los filtros y muestra resultados. Los cálculos están
en src/mercado_laboral.py y los gráficos en src/graficos_mercado_laboral.py.
"""
import streamlit as st

from src import config
from src import graficos_mercado_laboral as gr
from src import mercado_laboral as ml

MAX_PANELES = 8  # a partir de acá se avisa que hay muchos paneles

st.title("Mercado Laboral y Género")
st.markdown(
    "Evolución de la tasa de desempleo y de la distribución de la población "
    "(ocupados, desocupados e inactivos) por aglomerado, con la comparación "
    "entre varones y mujeres. Todos los valores están ponderados con "
    "`PONDERA`."
)


@st.cache_data(show_spinner="Leyendo los archivos de individuos...")
def cargar_datos():
    """Carga (una sola vez) los archivos de individuos de Mercado Laboral."""
    return ml.cargar_datos_individuos()


@st.cache_data(show_spinner=False)
def calcular_evolucion(_datos, desde, hasta, aglomerados, periodo,
                       trimestres):
    """Calcula la tabla de evolución para la selección actual."""
    return ml.preparar_datos_evolucion(
        _datos, desde, hasta, list(aglomerados), periodo, list(trimestres))


datos = cargar_datos()
if datos.empty:
    st.warning(
        "No se encontraron archivos de individuos de Mercado Laboral en "
        f"`{config.DIR_DATOS}`.")
    st.stop()

anios = ml.anios_disponibles(datos)
if len(anios) < config.MIN_ANIOS_B:
    st.warning(
        f"Hay datos de {len(anios)} año(s) ({', '.join(map(str, anios))}) y "
        f"este análisis necesita al menos {config.MIN_ANIOS_B}.")
    st.stop()

codigos = ml.aglomerados_disponibles(datos)
SEXOS = list(gr.COLORES_SEXO)

# ------------------------------- Filtros ----------------------------------
with st.container(border=True):
    izquierda, derecha = st.columns(2)
    with izquierda:
        desde, hasta = st.select_slider(
            "Rango de años", options=anios, value=(anios[0], anios[-1]),
            key="b_rango")
        periodo = st.radio(
            "Período", options=list(ml.GRUPOS_POR_PERIODO),
            format_func=str.capitalize, horizontal=True, key="b_periodo")
        if periodo == "trimestral":
            trimestres = st.multiselect(
                "Trimestres", options=[1, 2, 3, 4], default=[1, 2, 3, 4],
                format_func=lambda t: f"T{t}", key="b_trimestres")
        else:
            trimestres = [1, 2, 3, 4]
    with derecha:
        todos = st.checkbox("Todos los aglomerados", key="b_todos")
        if todos:
            aglomerados = codigos
        else:
            aglomerados = st.multiselect(
                "Aglomerados", options=codigos, default=codigos[:3],
                format_func=lambda c: config.AGLOMERADOS.get(c, c),
                key="b_aglomerados")
        sexos = st.multiselect(
            "Comparar por sexo", options=SEXOS, default=SEXOS,
            key="b_sexos")
        nombre_metrica = st.selectbox(
            "Indicador", options=list(ml.METRICAS_EVOLUCION),
            key="b_metrica")
metrica = ml.METRICAS_EVOLUCION[nombre_metrica]

try:
    ml.validar_rango_anios(datos, desde, hasta)
except ValueError as error:
    st.error(str(error))
    st.stop()
if not aglomerados or not sexos or not trimestres:
    st.info("Elegí al menos un aglomerado, un sexo y un trimestre.")
    st.stop()

tabla = calcular_evolucion(
    datos, desde, hasta, tuple(aglomerados), periodo, tuple(trimestres))
if tabla.empty:
    st.warning("No hay datos para la selección elegida.")
    st.stop()

if st.session_state.get("excluir_criticos"):
    st.caption(
        "Filtro CRÍTICO activo: este bloque ya excluye ESTADO = 0 y no "
        "usa la edad, por lo que sus resultados no cambian.")

# ---------------------------- Indicadores ---------------------------------
ind = ml.indicadores_principales(tabla, periodo)
hay_variacion = ind["periodo_inicial"] != ind["periodo"]
col1, col2, col3, col4 = st.columns(4)
col1.metric(
    f"Desempleo total ({ind['periodo']})",
    f"{ml.formatear_numero(ind['tasa_total'])} %",
    delta=(f"{ml.formatear_numero(ind['variacion_total'], True)} pp vs "
           f"{ind['periodo_inicial']}") if hay_variacion else None,
    delta_color="inverse")
col2.metric("Desempleo varones", f"{ml.formatear_numero(ind['tasa_varon'])} %")
col3.metric("Desempleo mujeres", f"{ml.formatear_numero(ind['tasa_mujer'])} %")
col4.metric("Brecha (mujer − varón)",
            f"{ml.formatear_numero(ind['brecha'], True)} pp")
st.caption(
    "Los indicadores consideran el conjunto de aglomerados elegidos. "
    "pp = puntos porcentuales.")

tab_evol, tab_dist, tab_brechas, tab_comp, tab_datos = st.tabs([
    "Evolución y género", "Distribución", "Brechas de género",
    "Comparativa de gráficos", "Datos"])

# --------------------------- Evolución y género ---------------------------
with tab_evol:
    if len(aglomerados) > MAX_PANELES:
        st.info(
            f"Elegiste {len(aglomerados)} aglomerados: se muestra un panel "
            "por cada uno. Para comparar muchos a la vez conviene el mapa "
            "de calor (pestaña Comparativa de gráficos).")
    st.altair_chart(gr.grafico_evolucion(tabla, metrica, sexos))
    st.subheader("Descripción de los resultados")
    for frase in ml.generar_descripcion(tabla, periodo):
        st.markdown(f"- {frase}")

# ------------------------------ Distribución ------------------------------
with tab_dist:
    sexo_dist = st.selectbox(
        "Población a mostrar", options=SEXOS, key="b_sexo_dist")
    st.altair_chart(gr.grafico_distribucion(
        ml.preparar_datos_distribucion(tabla, sexo_dist)))
    st.caption(
        "Cada barra suma 100 %: ocupados, desocupados e inactivos sobre la "
        "población con condición de actividad (se excluyen menores de 10 "
        "años y entrevistas no realizadas).")

# ----------------------------- Brechas de género --------------------------
with tab_brechas:
    brechas = ml.preparar_datos_brechas(tabla, periodo)
    st.altair_chart(gr.grafico_brechas(brechas, metrica))
    st.caption(
        "Brecha = valor de las mujeres − valor de los varones, en puntos "
        "porcentuales. Por encima de 0, el indicador es mayor en las "
        "mujeres.")

# -------------------------- Comparativa de gráficos -----------------------
with tab_comp:
    st.markdown(
        "Se analizaron tres gráficos con los mismos datos y el mismo "
        f"indicador (**{nombre_metrica}**).")
    st.subheader("1. Líneas con un panel por aglomerado (elegido)")
    st.altair_chart(gr.grafico_evolucion(tabla, metrica, sexos))
    st.subheader("2. Barras agrupadas")
    st.altair_chart(gr.grafico_barras_agrupadas(tabla, metrica, sexos))
    st.subheader("3. Mapa de calor")
    st.altair_chart(gr.grafico_mapa_calor(tabla, metrica, sexos))

    st.subheader("Fundamentación")
    st.table({
        "Dimensión": ["Tiempo", "Geografía", "Género", "Métrica"],
        "Líneas con paneles": [
            "Muy bien: la evolución es el eje horizontal.",
            "Bien con pocos aglomerados; se satura con muchos paneles.",
            "Muy bien: dos líneas en el mismo panel, la distancia entre "
            "ellas es la brecha.",
            "Muy bien: el eje vertical da el valor y el cursor el dato "
            "exacto."],
        "Barras agrupadas": [
            "Débil: solo muestra un período.",
            "Muy bien: ordena y compara aglomerados.",
            "Muy bien: las barras de varones y mujeres quedan juntas.",
            "Muy bien: la altura se compara fácilmente."],
        "Mapa de calor": [
            "Bien: una columna por período.",
            "Muy bien con muchos aglomerados.",
            "Regular: necesita un panel por sexo y comparar colores.",
            "Débil: el color es menos preciso que la posición o la "
            "longitud."],
    })
    st.markdown(
        "**Elección:** las líneas con un panel por aglomerado y un color "
        "por sexo son el único gráfico de los tres que muestra a la vez "
        "las cuatro dimensiones (tiempo, geografía, género y métrica) sin "
        "perder información. Las barras sirven como complemento para "
        "comparar aglomerados en el último período y el mapa de calor "
        "cuando se eligen muchos aglomerados.")

# --------------------------------- Datos ----------------------------------
with tab_datos:
    st.dataframe(tabla, hide_index=True)
    st.download_button(
        "Descargar CSV", tabla.to_csv(index=False).encode("utf-8"),
        file_name="mercado_laboral_evolucion.csv", mime="text/csv")