import streamlit as st
import sys
from pathlib import Path
st.set_page_config(page_title="Metricas") #aca se puede configurar algunas cosas de la page como el nombre

pg = st.navigation ({
"Dashboard EPH":[
    st.Page("pages/01_inicio.py", title="Inicio"),
    st.Page("pages/02_carga_y_estado.py", title="Carga y Estado"),
    st.Page("pages/03_mercado_laboral.py", title="Mercado Laboral y Género"),
    st.Page("pages/04_hogares_tecnologia.py", title="Hogares y Tecnología"),
    st.Page("pages/05_mapa.py", title="Mapa Georreferenciado"),
    st.Page("pages/06_ayuda.py", title="Hoja de ayuda"),
]
})
root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

pg.run()

