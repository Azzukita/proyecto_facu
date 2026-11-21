"""P4: Panel de control de Hogares y Tecnología (Bloque C).

La página solo arma la interfaz: todo el cálculo está en
src/hogares_tecnologia.py.
"""
import sys
from pathlib import Path

import altair as alt
import streamlit as st

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.append(str(RAIZ))

from src import config, data_loader, hogares_tecnologia as ht  # noqa: E402


@st.cache_data(show_spinner="Leyendo el informe de tecnología...")
def informe():
    """Carga (una sola vez) el informe de la primera etapa."""
    return ht.cargar_informe_tecnologia()


@st.cache_data(show_spinner="Buscando archivos de datos...")
def anios_con_cruce():
    """Devuelve los años en que se puede cruzar TIC con vivienda."""
    return ht.anios_disponibles_cruce(data_loader.escanear_datos())


@st.cache_data(show_spinner="Cruzando hogares...")
def base_del_anio(anio):
    """Arma (una sola vez por año) la base cruzada de hogares."""
    return ht.armar_base_cruce(anio)


st.title("Hogares y Tecnología")
st.markdown(
    "Acceso a computadora, internet y celular, y cómo se relaciona la "
    "**calidad tecnológica** de los hogares con sus condiciones de vivienda.")

tab_informe, tab_cruce = st.tabs(
    ["Penetración tecnológica", "Calidad tecnológica y vivienda"])

# -----------------------------------------------------------------------------
# Parte 1: informes de la primera etapa
# -----------------------------------------------------------------------------
with tab_informe:
    datos = informe()
    anios = ht.anios_del_informe(datos)
    if not anios:
        st.warning(
            "No se encontró el informe de tecnología en la carpeta de "
            f"salida (`{config.PATRON_INFORME_TECNOLOGIA}`). Ejecutá el "
            "notebook de Ciencia y Tecnología de la primera etapa.")
    else:
        col_anio, col_nivel = st.columns(2)
        anio = col_anio.selectbox("Año", anios, index=len(anios) - 1,
                                  key="pen_anio")
        nivel_texto = col_nivel.radio("Organización geográfica",
                                      ["Región", "Aglomerado"],
                                      horizontal=True, key="pen_nivel")
        nivel = {"Región": "region", "Aglomerado": "aglomerado"}[nivel_texto]
        tabla = ht.tabla_penetracion(datos, anio, nivel)
        elegidos = st.multiselect(
            f"{nivel_texto}(s) a mostrar",
            options=tabla["Nombre"].tolist(),
            default=ht.opciones_por_defecto(tabla, nivel),
            key=f"pen_sel_{nivel}")
        if not elegidos:
            st.info("Elegí al menos un grupo para ver los resultados.")
        else:
            seleccion = ht.filtrar_penetracion(tabla, elegidos)
            st.bar_chart(seleccion, x="Nombre",
                         y=["Computadora (%)", "Internet (%)", "Celular (%)"],
                         y_label="% de hogares", x_label=nivel_texto)
            st.dataframe(seleccion, hide_index=True)
            st.download_button(
                "Descargar esta tabla (CSV)", ht.a_csv(seleccion),
                file_name=f"penetracion_{nivel}_{anio}.csv",
                mime="text/csv", key="pen_descarga")

# -----------------------------------------------------------------------------
# Parte 2: cruce con vivienda
# -----------------------------------------------------------------------------
with tab_cruce:
    anios_cruce = anios_con_cruce()
    if not anios_cruce:
        st.warning(
            "No hay años con los dos archivos necesarios: hogares de "
            "Ciencia y Tecnología y hogares de Mercado Laboral "
            f"{config.TRIMESTRE_CRUCE_TIC} del mismo año.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    anio_c = col1.selectbox("Año", anios_cruce, index=len(anios_cruce) - 1,
                            key="cruce_anio")
    opciones_region = [config.OPCION_TODAS_REGIONES,
                       *config.NOMBRES_REGIONES.values()]
    region = col2.selectbox("Región", opciones_region, key="cruce_region")
    variables = list(config.VARIABLES_VIVIENDA)
    variable = col3.selectbox(
        "Variable de vivienda", variables,
        index=variables.index(config.VARIABLE_VIVIENDA_DEFECTO),
        format_func=lambda v: config.VARIABLES_VIVIENDA[v],
        key="cruce_variable")

    with st.expander("Opciones avanzadas"):
        col_peso = st.selectbox(
            "Peso para ponderar", config.COLS_PESO_CRUCE, key="cruce_peso",
            help="POND_TIC es el factor de expansión del módulo de "
                 "tecnología (recomendado). PONDERA es el de la EPH general.")

    try:
        base, diagnostico = base_del_anio(anio_c)
    except (FileNotFoundError, ValueError, OSError) as error:
        st.error(f"No se pudo armar el cruce: {error}")
        st.stop()

    codigo_region = {nombre: cod for cod, nombre
                     in config.NOMBRES_REGIONES.items()}.get(region)
    seleccion = ht.filtrar_region(base, codigo_region)
    resultado = ht.porcentaje_por_vivienda(seleccion, variable, col_peso)

    if resultado.empty:
        st.info("No hay hogares con datos válidos para esta selección.")
    else:
        categorias = list(config.CATEGORIAS_CALIDAD_TEC.values())
        grupos = list(dict.fromkeys(resultado[ht.COL_GRUPO]))
        grafico = alt.Chart(resultado).mark_bar().encode(
            y=alt.Y(f"{ht.COL_GRUPO}:N", title=None, sort=grupos,
                    axis=alt.Axis(labelLimit=400)),
            x=alt.X(f"{ht.COL_PORCENTAJE}:Q", title="% de hogares",
                    scale=alt.Scale(domain=[0, 100])),
            color=alt.Color(f"{ht.COL_CATEGORIA}:N", sort=categorias,
                            scale=alt.Scale(domain=categorias),
                            title="Calidad tecnológica",
                            legend=alt.Legend(labelLimit=400)),
            tooltip=[ht.COL_GRUPO, ht.COL_CATEGORIA, ht.COL_PORCENTAJE,
                     ht.COL_MUESTRA],
        )
        st.altair_chart(grafico)

        st.subheader("Descripción de los resultados")
        total = ht.resumir_total(seleccion, col_peso)
        st.markdown(ht.describir_resultados(
            resultado, total, anio_c, region, variable, col_peso,
            ht.contar_descartados(seleccion, col_peso)))

        st.dataframe(resultado, hide_index=True)
        st.download_button(
            "Descargar los datos de esta selección (CSV)",
            ht.a_csv(resultado),
            file_name=(f"calidad_tecnologica_{variable}_{anio_c}_"
                       f"{codigo_region or 'todas'}.csv"),
            mime="text/csv", key="cruce_descarga")

    with st.expander("Calidad del cruce entre archivos"):
        st.write(
            f"Clave de unión: `{', '.join(config.COLS_ID_HOGAR)}`. "
            f"Hogares TIC: **{diagnostico['hogares_tic']}**; hogares de "
            f"Mercado Laboral {config.TRIMESTRE_CRUCE_TIC}: "
            f"**{diagnostico['hogares_vivienda']}**.")
        st.write(
            f"Con pareja: **{diagnostico['con_pareja']}** · TIC sin pareja "
            f"en vivienda: **{diagnostico['sin_pareja_en_vivienda']}** · "
            f"solo en vivienda: **{diagnostico['solo_en_vivienda']}** · "
            f"claves repetidas (TIC / vivienda): "
            f"**{diagnostico['claves_repetidas_tic']} / "
            f"{diagnostico['claves_repetidas_vivienda']}** · sin "
            f"computadora o internet válidos: "
            f"**{diagnostico['hogares_sin_clasificar']}**.")