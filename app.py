import importlib

import pandas as pd
import streamlit as st

import modules.dni as dni
import modules.socios as socios

importlib.reload(socios)
importlib.reload(dni)

st.set_page_config(
    page_title="Grido Hub",
    page_icon="🍦",
    layout="wide",
)

st.sidebar.title("Grido Hub")

modulo = st.sidebar.radio(
    "Módulos",
    [
        "🏠 Inicio",
        "👥 Socios",
        "📢 Marketing",
        "🤖 IA",
        "⚙️ Configuración",
    ],
    key="menu_principal",
)

st.title("🍦 Grido Hub")
st.caption("Versión 0.1.0")

resumen_general = socios.obtener_resumen_base()

if "dni_chrome_abierto" not in st.session_state:
    st.session_state["dni_chrome_abierto"] = False

if modulo == "🏠 Inicio":

    st.success("Proyecto inicializado correctamente.")
    st.subheader("Estado")

    if resumen_general["existe"]:
        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Socios históricos",
            resumen_general["socios_historicos"],
        )

        c2.metric(
            "En Favoritos actual",
            resumen_general["en_favoritos_actual"],
        )

        c3.metric(
            "Pendientes DNI",
            resumen_general["pendientes_dni"],
        )

        st.caption(
            "Última actualización: "
            f"{resumen_general['ultima_actualizacion']}"
        )

    else:
        st.info(
            "Todavía no existe una base de clientes. "
            "Entrá en Socios y cargá el primer archivo Favoritos."
        )

elif modulo == "👥 Socios":

    st.header("👥 Socios")

    historicos = resumen_general["socios_historicos"]
    actuales = resumen_general["en_favoritos_actual"]
    pendientes = resumen_general["pendientes_dni"]
    ultima_actualizacion = resumen_general["ultima_actualizacion"]

    c1, c2, c3, c4 = st.columns(4)

    tarjeta_historicos = c1.empty()
    tarjeta_actuales = c2.empty()
    tarjeta_nuevos = c3.empty()
    tarjeta_pendientes = c4.empty()

    tarjeta_historicos.metric("Socios históricos", historicos)
    tarjeta_actuales.metric("En Favoritos actual", actuales)
    tarjeta_nuevos.metric("Nuevos última carga", "-")
    tarjeta_pendientes.metric("Pendientes DNI", pendientes)

    if resumen_general["existe"]:
        st.caption(
            f"Última actualización: {ultima_actualizacion}"
        )
    else:
        st.info(
            "Este parece ser el primer uso. "
            "Cargá el archivo Favoritos para crear la base."
        )

    st.divider()

    favoritos = st.file_uploader(
        "Favoritos del Club Grido",
        type=["csv", "xlsx"],
        key="archivo_favoritos",
    )

    col1, col2 = st.columns(2)

    with col1:
        actualizar = st.button(
            "🔄 Actualizar Base",
            use_container_width=True,
            key="actualizar_base",
        )

    with col2:
        preparar_dni = st.button(
            "🆔 Obtener DNI",
            use_container_width=True,
            disabled=not resumen_general["existe"],
            key="obtener_dni",
        )

    if preparar_dni:
        cantidad = dni.obtener_cantidad_pendientes()
        por_procesar = dni.obtener_cantidad_por_procesar()

        if cantidad == 0:
            st.success("No hay socios pendientes de DNI.")
        else:
            st.info(
                f"Hay {cantidad} socios sin DNI. "
                f"{por_procesar} todavía no fueron procesados."
            )

            try:
                with st.spinner("Abriendo Chrome..."):
                    dni.iniciar_navegador()

                st.session_state["dni_chrome_abierto"] = True

                st.success(
                    "Chrome abierto. Iniciá sesión, resolvé el captcha, "
                    "entrá a Consulta de Socios y marcá manualmente "
                    "'Solo por email'. Después volvé acá."
                )

            except Exception as error:
                st.error(
                    f"No se pudo abrir Chrome: {error}"
                )

    if st.session_state["dni_chrome_abierto"]:

        st.subheader("Prueba controlada")

        cantidad_lote = st.selectbox(
            "Cantidad a procesar",
            options=[1, 5],
            index=1,
            key="cantidad_lote_dni",
        )

        iniciar_lote = st.button(
            f"▶ Procesar {cantidad_lote} socios",
            use_container_width=True,
            key="procesar_lote_dni",
        )

        if iniciar_lote:
            barra = st.progress(0)
            estado_actual = st.empty()
            log = st.empty()
            resultados_visibles = []

            def actualizar_progreso(resultado):
                avance = (
                    resultado["posicion"]
                    / resultado["total"]
                )

                barra.progress(avance)

                estado_actual.write(
                    f"Procesando {resultado['posicion']} "
                    f"de {resultado['total']}: "
                    f"**{resultado['email']}**"
                )

                simbolo = {
                    "OK": "✅",
                    "SIN_DNI": "⚠️",
                    "ERROR": "❌",
                }.get(resultado["estado"], "•")

                texto = (
                    f"{simbolo} {resultado['email']} — "
                    f"{resultado['estado']}"
                )

                if resultado["dni"]:
                    texto += f" — DNI {resultado['dni']}"

                resultados_visibles.append(texto)

                log.markdown(
                    "\n\n".join(resultados_visibles)
                )

            try:
                with st.spinner(
                    "Procesando el lote de DNI..."
                ):
                    resumen_lote = dni.procesar_lote(
                        cantidad_lote,
                        callback=actualizar_progreso,
                    )

                barra.progress(1.0)
                estado_actual.success("Lote finalizado.")

                r1, r2, r3, r4 = st.columns(4)

                r1.metric(
                    "Procesados",
                    resumen_lote["procesados"],
                )
                r2.metric(
                    "Encontrados",
                    resumen_lote["encontrados"],
                )
                r3.metric(
                    "Sin DNI",
                    resumen_lote["sin_dni"],
                )
                r4.metric(
                    "Errores",
                    resumen_lote["errores"],
                )

                tarjeta_pendientes.metric(
                    "Pendientes DNI",
                    resumen_lote["pendientes_restantes"],
                )

                st.caption(
                    "Pendientes sin procesar automáticamente: "
                    f"{resumen_lote['por_procesar']}. "
                    "Se creó un backup antes del lote y cada "
                    "resultado fue guardado inmediatamente."
                )

            except Exception as error:
                st.error(
                    f"Falló el procesamiento del lote: {error}"
                )

    if actualizar:

        if favoritos is None:
            st.warning(
                "Primero seleccioná el archivo Favoritos."
            )

        else:
            try:
                with st.spinner(
                    "Actualizando la base de socios..."
                ):

                    if favoritos.name.lower().endswith(".csv"):

                        try:
                            df_favoritos = pd.read_csv(
                                favoritos,
                                sep=";",
                                engine="python",
                            )

                            if len(df_favoritos.columns) == 1:
                                raise ValueError(
                                    "Separador incorrecto"
                                )

                        except Exception:
                            favoritos.seek(0)

                            df_favoritos = pd.read_csv(
                                favoritos,
                                sep=",",
                                engine="python",
                            )

                    else:
                        df_favoritos = pd.read_excel(
                            favoritos
                        )

                    resultado = socios.actualizar_base(
                        df_favoritos
                    )

                tarjeta_historicos.metric(
                    "Socios históricos",
                    resultado["socios_historicos"],
                )

                tarjeta_actuales.metric(
                    "En Favoritos actual",
                    resultado["en_favoritos_actual"],
                )

                tarjeta_nuevos.metric(
                    "Nuevos última carga",
                    resultado["nuevos"],
                )

                tarjeta_pendientes.metric(
                    "Pendientes DNI",
                    resultado["pendientes_dni"],
                )

                st.success(
                    "Base actualizada correctamente."
                )

                st.caption(
                    "Ya no aparecen actualmente en Favoritos: "
                    f"{resultado['ya_no_aparecen']}. "
                    "Igualmente permanecen disponibles "
                    "para campañas."
                )

            except Exception as error:
                st.error(
                    f"No se pudo actualizar la base: {error}"
                )

else:

    st.info("Módulo en desarrollo.")
