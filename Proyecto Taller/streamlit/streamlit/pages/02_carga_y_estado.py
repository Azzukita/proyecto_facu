import streamlit as st
from src import config
from src.panel_calidad import (
    cargar_todos_los_informes,
    informes_de_faltantes,
    informes_de_consistencia,
    extraer_datos_completitud,
    armar_tabla_faltantes,
    promedio_por_etiqueta,
    extraer_datos_consistencia,
    contar_por_etiqueta,
    tabla_registros,
    columnas_sin_datos,
)

st.title("Panel de Control: Completitud y Calidad de Datos")
st.markdown("Análisis de faltantes e inconsistencias adaptado por rol.")

diccionario_informes = cargar_todos_los_informes()

if not diccionario_informes:
    st.warning("No se encontraron archivos JSON de reportes en la carpeta de salida.")
else:
    rol_seleccionado = st.selectbox(
        "Seleccione su rol de usuario:",
        options=list(config.ROLES.keys()),
        format_func=lambda x: x.capitalize()
    )

    columnas_del_rol = config.ROLES.get(rol_seleccionado, [])
    st.info(f"El rol **{rol_seleccionado}** analiza las columnas: `{', '.join(columnas_del_rol) if columnas_del_rol else 'Todas'}`")

    # Punto 4: botón para excluir los registros CRÍTICO.
    # Se guarda en session_state para que también lo usen las demás páginas.
    if "excluir_criticos" not in st.session_state:
        st.session_state["excluir_criticos"] = False

    if st.session_state["excluir_criticos"]:
        texto_boton = "Volver a incluir registros de tipo CRÍTICO"
        tipo_boton = "secondary"  
    else:
        texto_boton = "Excluir registros de tipo CRÍTICO"
        tipo_boton = "primary"    

    if st.button(texto_boton, type=tipo_boton):
        st.session_state["excluir_criticos"] = not st.session_state["excluir_criticos"]
        st.rerun()

    excluir_criticos = st.session_state["excluir_criticos"]
    if excluir_criticos:
        st.info("Los registros CRÍTICO están excluidos del análisis.")

    st.divider()

   
    tab_faltantes, tab_inconsistencias = st.tabs(["Faltantes", "Inconsistencias"])

  
    with tab_faltantes:
        informes_falt = informes_de_faltantes(diccionario_informes)

        if not informes_falt:
            st.info("No hay informes de faltantes en la carpeta de salida.")
        else:
            archivo_elegido = st.selectbox(
                "Seleccione el reporte a analizar:",
                options=list(informes_falt.keys()),
                key="reporte_faltantes"
            )
            datos_completitud = extraer_datos_completitud(informes_falt[archivo_elegido])
            por_trimestre = datos_completitud["por_trimestre"]

         
            trimestre_elegido = st.selectbox(
                "Seleccione el trimestre:",
                options=list(por_trimestre.keys()),
                key="trimestre_faltantes"
            )

         
            columnas_dict = por_trimestre[trimestre_elegido].get("columnas", {})

           
            etiquetas_disponibles = ["Supera umbral", "No supera umbral"]
            etiquetas_seleccionadas = st.multiselect(
                "Filtrar por estado de completitud:",
                options=etiquetas_disponibles,
                default=etiquetas_disponibles
            )

            
            df_rol = armar_tabla_faltantes(columnas_dict, columnas_del_rol, etiquetas_seleccionadas)

            if not df_rol.empty:
                st.subheader(f"Métricas de Completitud para el rol: {rol_seleccionado.capitalize()}")

                df_agrupado = promedio_por_etiqueta(df_rol)

                cols_metricas = st.columns(len(df_agrupado) if len(df_agrupado) > 0 else 1)
                for idx, row in df_agrupado.iterrows():
                    with cols_metricas[idx % len(cols_metricas)]:
                        st.metric(label=f"Estado: {row['Etiqueta']}", value=f"{row['Porcentaje Faltantes (%)']:.2f}% prom. faltantes")

                st.markdown("### Gráfico de Faltantes por Columna")
        
                st.bar_chart(
                    df_rol,
                    x="Columna",
                    y=["Porcentaje Válidos (%)", "Porcentaje Faltantes (%)", "Porcentaje No Corresponde (%)"],
                    color=["#2ecc71", "#e74c3c", "#95a5a6"],
                    horizontal=True
                )

                faltan_en_informe = columnas_sin_datos(columnas_dict, columnas_del_rol)
                if faltan_en_informe:
                    st.caption(f"Columnas del rol que no están en este informe: {', '.join(faltan_en_informe)}")

                with st.expander("Ver tabla detallada de completitud por columna"):
                    st.dataframe(df_rol, use_container_width=True)

            else:
                st.warning("No se registraron columnas que coincidan con el rol y los filtros seleccionados.")

    with tab_inconsistencias:
        informes_inc = informes_de_consistencia(diccionario_informes)

        if not informes_inc:
            st.info("No hay informes de inconsistencias en la carpeta de salida.")
        else:
            archivo_inc = st.selectbox(
                "Seleccione el reporte a analizar:",
                options=list(informes_inc.keys()),
                key="reporte_inconsistencias"
            )
            datos_consistencia = extraer_datos_consistencia(informes_inc[archivo_inc])
            por_trimestre_inc = datos_consistencia["por_trimestre"]

            trimestre_inc = st.selectbox(
                "Seleccione el trimestre:",
                options=list(por_trimestre_inc.keys()),
                key="trimestre_inconsistencias"
            )
            reglas_dict = por_trimestre_inc[trimestre_inc].get("reglas", {})

            etiquetas_inc = list(config.ORDEN_ETIQUETAS)
            if excluir_criticos:
                etiquetas_inc.remove(config.ETIQUETA_CRITICO)

            etiquetas_elegidas = st.multiselect(
                "Seleccione las etiquetas:",
                options=etiquetas_inc,
                default=etiquetas_inc
            )

            df_conteo = contar_por_etiqueta(reglas_dict, columnas_del_rol, etiquetas_elegidas)
            st.markdown("### Registros afectados por etiqueta")
            st.bar_chart(df_conteo, x="Etiqueta", y="Registros Afectados", horizontal=True)

            df_registros = tabla_registros(reglas_dict, columnas_del_rol, etiquetas_elegidas)
            with st.expander("Ver cantidad por etiqueta"):
                st.dataframe(df_conteo, use_container_width=True)
