"""P1: Inicio. Presentación de la app, integrantes y tutorial interactivo.

Esta página no calcula nada: solo muestra texto y guía al usuario por las
demás páginas del dashboard.
"""
import streamlit as st

TITULO = "PyEPH.AR"
INTEGRANTES = (
    "Lucas Pascual Martina",
    "Felipe Marín Russo",
    "Lautaro Agustín López",
    "Gonzalo Ariel Escribano Echever",
)
# Cada paso del tutorial: título, explicación y página a la que lleva.
PASOS_TUTORIAL = (
    {
        "titulo": "Carga y Estado",
        "texto": "Empezá acá: muestra qué años y trimestres hay disponibles "
                 "y los informes de calidad de datos. Podés elegir un rol "
                 "(docente, investigador o analista), filtrar por etiqueta "
                 "(CRÍTICO, ADVERTENCIA, INFO, ERROR, VERIFICAR), "
                 "inspeccionar "
                 "los registros afectados y decidir si se excluyen los "
                 "CRÍTICO del resto del análisis.",
        "pagina": "pages/02_carga_y_estado.py",
    },
    {
        "titulo": "Mercado Laboral y Género",
        "texto": "Tasa de desempleo y distribución de ocupados, desocupados "
                 "e inactivos. Elegí un rango de años (mínimo 2) y los "
                 "aglomerados para ver la evolución y las brechas de género. "
                 "Una segunda pestaña compara tres gráficos posibles.",
        "pagina": "pages/03_mercado_laboral.py",
    },
    {
        "titulo": "Hogares y Tecnología",
        "texto": "Dos pestañas. La primera muestra la penetración de "
                 "computadora, internet y celular por región o aglomerado. "
                 "La segunda cruza la calidad tecnológica de los hogares "
                 "con su vivienda: elegí año, región y variable, mirá el "
                 "gráfico y descargá los datos en CSV.",
        "pagina": "pages/04_hogares_tecnologia.py",
    },
    {
        "titulo": "Mapa Georreferenciado",
        "texto": "Los resultados de mercado laboral (por trimestre o anual) "
                 "y de tecnología sobre el mapa de Argentina, por "
                 "aglomerado. La tecnología se puede filtrar por tipo de "
                 "vivienda.",
        "pagina": "pages/05_mapa.py",
    },
    {
        "titulo": "Hoja de ayuda",
        "texto": "Ejemplos de pandas usados en el proyecto: sum() y agg() "
                 "con groupby(), merge() entre los datasets, y pivot_table() "
                 "frente a groupby() con unstack().",
        "pagina": "pages/06_ayuda.py",
    },
)
CLAVE_PASO = "tutorial_paso"


def abrir_tutorial():
    """Muestra el tutorial desde el primer paso."""
    st.session_state[CLAVE_PASO] = 0


def cerrar_tutorial():
    """Oculta el tutorial."""
    st.session_state[CLAVE_PASO] = None


def mover_tutorial(delta):
    """Avanza o retrocede un paso del tutorial, sin salirse del rango.

    Args:
        delta: 1 para avanzar, -1 para retroceder.
    """
    paso = st.session_state[CLAVE_PASO] + delta
    st.session_state[CLAVE_PASO] = max(0, min(paso, len(PASOS_TUTORIAL) - 1))


def mostrar_tutorial():
    """Dibuja el paso actual del tutorial con sus botones."""
    paso = st.session_state[CLAVE_PASO]
    total = len(PASOS_TUTORIAL)
    datos = PASOS_TUTORIAL[paso]
    with st.container(border=True):
        st.progress((paso + 1) / total, text=f"Paso {paso + 1} de {total}")
        st.subheader(datos["titulo"])
        st.write(datos["texto"])
        st.page_link(datos["pagina"], label=f"Ir a {datos['titulo']}")
        anterior, siguiente, cerrar = st.columns(3)
        anterior.button("Anterior", disabled=paso == 0, width="stretch",
                        on_click=mover_tutorial, args=(-1,))
        siguiente.button("Siguiente", disabled=paso == total - 1,
                         width="stretch", on_click=mover_tutorial, args=(1,))
        cerrar.button("Cerrar tutorial", width="stretch",
                      on_click=cerrar_tutorial)


st.title(TITULO)
st.markdown(
    "Dashboard interactivo para analizar la **Encuesta Permanente de Hogares "
    "(EPH)** del INDEC. Integra los datos de **Mercado Laboral** y de "
    "**Ciencia y Tecnología**: permite revisar la calidad de los datos, "
    "comparar el desempleo y las brechas de género, relacionar la "
    "tecnología de los hogares con su vivienda y verlo todo sobre el mapa "
    "de Argentina.")
st.caption("Proyecto del Taller de Lenguajes (Redictado 2026), segunda etapa.")

st.subheader("Integrantes")
for integrante in INTEGRANTES:
    st.markdown(f"- {integrante}")

st.subheader("Cómo usar la aplicación")
st.write("Usá el menú lateral para moverte entre las páginas, o seguí el "
         "tutorial paso a paso.")
if st.session_state.get(CLAVE_PASO) is None:
    st.button("Comenzar tutorial", type="primary", on_click=abrir_tutorial)
else:
    mostrar_tutorial()