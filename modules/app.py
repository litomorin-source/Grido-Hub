import pandas as pd
import streamlit as st

import modules.dni as dni
import modules.segmentacion as segmentacion
import modules.socios as socios


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

if "dni_chrome_preparado" not in st.session_state:
    st.session_state["dni_chrome_preparado"] = False


def leer_favoritos(archivo):
    if archivo.name.lower().endswith(".csv"):
        try:
            dataframe = pd.read_csv(
                archivo,
                sep=";",
                engine="python",
            )

            if len(dataframe.columns) == 1:
                raise ValueError(
                    "Separador incorrecto"
                )

            return dataframe

        except Exception:
            archivo.seek(0)

            return pd.read_csv(
                archivo,
                sep=",",
                engine="python",
            )

    return pd.read_excel(archivo)


def formatear_tiempo(segundos):
    segundos = int(float(segundos or 0))
    minutos, segundos = divmod(segundos, 60)
    horas, minutos = divmod(minutos, 60)

    if horas:
        return (
            f"{horas:02d}:"
            f"{minutos:02d}:"
            f"{segundos:02d}"
        )

    return f"{minutos:02d}:{segundos:02d}"


@st.fragment(run_every="1s")
def panel_procesamiento_dni():
    estado = dni.obtener_estado_procesamiento()
    estado_nombre = estado.get(
        "estado",
        "inactivo",
    )

    if estado_nombre == "inactivo":
        return

    st.subheader("Procesamiento DNI")

    total = max(
        int(estado.get("total", 0)),
        1,
    )

    procesados = int(
        estado.get("procesados", 0)
    )

    avance = min(
        procesados / total,
        1.0,
    )

    st.progress(avance)

    if estado.get("email_actual"):
        st.write(
            "Procesando: "
            f"**{estado['email_actual']}**"
        )

    st.caption(
        f"{procesados} de "
        f"{estado.get('total', 0)} · "
        "Tiempo: "
        f"{formatear_tiempo(estado.get('segundos', 0))}"
    )

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Procesados",
        procesados,
    )

    m2.metric(
        "Encontrados",
        estado.get("encontrados", 0),
    )

    m3.metric(
        "Sin DNI",
        estado.get("sin_dni", 0),
    )

    m4.metric(
        "Errores",
        estado.get("errores", 0),
    )

    if estado_nombre in {
        "ejecutando",
        "deteniendo",
    }:
        if estado_nombre == "deteniendo":
            st.warning(
                estado.get(
                    "mensaje",
                    "Deteniendo...",
                )
            )
        else:
            st.info(
                estado.get(
                    "mensaje",
                    "Procesando...",
                )
            )

        if st.button(
            "⏹ Detener al terminar el socio actual",
            use_container_width=True,
            disabled=(
                estado_nombre == "deteniendo"
            ),
            key="detener_lote_dni",
        ):
            dni.detener_procesamiento()
            st.rerun(scope="fragment")

    elif estado_nombre == "finalizado":
        st.success(
            estado.get(
                "mensaje",
                "Lote finalizado.",
            )
        )

    elif estado_nombre == "detenido":
        st.warning(
            estado.get(
                "mensaje",
                "Proceso detenido.",
            )
        )

    elif estado_nombre == "error":
        st.error(
            "El lote terminó con error: "
            f"{estado.get('mensaje', '')}"
        )

    st.caption(
        "Sin DNI en la base: "
        f"{estado.get('pendientes_restantes', 0)} · "
        "Pendientes para procesar/reintentar: "
        f"{estado.get('por_procesar', 0)}"
    )

    log = estado.get("log", [])

    if log:
        with st.expander(
            "Ver últimos resultados",
            expanded=(
                estado_nombre
                in {
                    "finalizado",
                    "detenido",
                    "error",
                }
            ),
        ):
            for item in reversed(log):
                simbolo = {
                    "OK": "✅",
                    "SIN_DNI": "⚠️",
                    "ERROR": "❌",
                }.get(
                    item.get("estado"),
                    "•",
                )

                texto = (
                    f"{simbolo} "
                    f"{item.get('email', '')} "
                    f"— {item.get('estado', '')}"
                )

                if item.get("dni"):
                    texto += (
                        f" — DNI {item['dni']}"
                    )

                st.write(texto)


if modulo == "🏠 Inicio":

    st.success(
        "Proyecto inicializado correctamente."
    )

    st.subheader("Estado")

    if resumen_general["existe"]:
        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Socios históricos",
            resumen_general[
                "socios_historicos"
            ],
        )

        c2.metric(
            "En Favoritos actual",
            resumen_general[
                "en_favoritos_actual"
            ],
        )

        c3.metric(
            "Pendientes DNI",
            resumen_general[
                "pendientes_dni"
            ],
        )

        st.caption(
            "Última actualización: "
            f"{resumen_general['ultima_actualizacion']}"
        )

    else:
        st.info(
            "Todavía no existe una base de clientes. "
            "Entrá en Socios y cargá el primer "
            "archivo Favoritos."
        )

elif modulo == "👥 Socios":

    st.header("👥 Socios")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Socios históricos",
        resumen_general[
            "socios_historicos"
        ],
    )

    c2.metric(
        "En Favoritos actual",
        resumen_general[
            "en_favoritos_actual"
        ],
    )

    c3.metric(
        "Pendientes DNI",
        resumen_general[
            "pendientes_dni"
        ],
    )

    c4.metric(
        "Por procesar",
        dni.obtener_cantidad_por_procesar(),
    )

    if resumen_general["existe"]:
        st.caption(
            "Última actualización: "
            f"{resumen_general['ultima_actualizacion']}"
        )

    st.divider()

    st.subheader("Actualizar socios")

    favoritos = st.file_uploader(
        "Favoritos del Club Grido",
        type=["csv", "xlsx"],
        key="archivo_favoritos",
    )

    if st.button(
        "🔄 Actualizar Base",
        use_container_width=True,
        key="actualizar_base",
    ):
        if favoritos is None:
            st.warning(
                "Primero seleccioná el archivo Favoritos."
            )
        else:
            try:
                with st.spinner(
                    "Actualizando la base de socios..."
                ):
                    resultado = socios.actualizar_base(
                        leer_favoritos(favoritos)
                    )

                st.success(
                    "Base actualizada correctamente. "
                    f"Nuevos: {resultado['nuevos']}."
                )

                st.rerun()

            except Exception as error:
                st.error(
                    "No se pudo actualizar la base: "
                    f"{error}"
                )

    st.divider()

    st.subheader("Obtener DNI")

    cantidad_sin_dni = (
        dni.obtener_cantidad_pendientes()
    )

    cantidad_por_procesar = (
        dni.obtener_cantidad_por_procesar()
    )

    st.write(
        f"**{cantidad_sin_dni}** socios "
        "no tienen DNI. "
        f"**{cantidad_por_procesar}** están "
        "pendientes de procesamiento o reintento."
    )

    if st.button(
        "🌐 Abrir / conectar Chrome",
        use_container_width=True,
        disabled=not resumen_general["existe"],
        key="abrir_chrome_dni",
    ):
        try:
            with st.spinner(
                "Abriendo Chrome..."
            ):
                dni.iniciar_navegador()

            st.session_state[
                "dni_chrome_preparado"
            ] = True

            st.success(
                "Chrome listo. Entrá a Consulta "
                "de Socios y marcá manualmente "
                "'Solo por email'."
            )

        except Exception as error:
            st.error(
                "No se pudo abrir Chrome: "
                f"{error}"
            )

    lote_activo = dni.procesamiento_activo()

    cantidad_lote = st.selectbox(
        "Cantidad a procesar",
        options=[1, 5, 20, 30, "Todos"],
        index=1,
        disabled=lote_activo,
        key="cantidad_lote_dni",
    )

    if st.button(
        "▶ Iniciar procesamiento",
        use_container_width=True,
        disabled=(
            not st.session_state[
                "dni_chrome_preparado"
            ]
            or lote_activo
            or cantidad_por_procesar == 0
        ),
        key="iniciar_lote_dni",
    ):
        try:
            dni.iniciar_procesamiento(
                cantidad_lote
            )

            st.success(
                "Procesamiento iniciado. "
                "Podés detenerlo cuando quieras."
            )

            st.rerun()

        except Exception as error:
            st.error(
                "No se pudo iniciar el lote: "
                f"{error}"
            )

    if not st.session_state[
        "dni_chrome_preparado"
    ]:
        st.caption(
            "Primero abrí Chrome, iniciá sesión, "
            "entrá a Consulta de Socios y marcá "
            "'Solo por email'."
        )

    panel_procesamiento_dni()

elif modulo == "📢 Marketing":

    st.header("📢 Marketing")
    st.subheader("🎯 Segmentación")

    tipo_segmento = st.selectbox(
        "Tipo de segmento",
        options=[
            "Cumpleaños por mes",
        ],
        key="tipo_segmento_marketing",
    )

    if tipo_segmento == "Cumpleaños por mes":

        mes = st.selectbox(
            "Mes de cumpleaños",
            options=list(
                segmentacion.MESES.keys()
            ),
            key="mes_cumpleanios",
        )

        if st.button(
            "🎂 Generar segmento",
            use_container_width=True,
            key="generar_segmento_cumpleanios",
        ):
            try:
                with st.spinner(
                    "Generando el segmento..."
                ):
                    resultado = (
                        segmentacion
                        .segmentar_cumpleanios(mes)
                    )

                st.session_state[
                    "segmento_cumpleanios"
                ] = resultado

            except Exception as error:
                st.error(
                    "No se pudo generar el segmento: "
                    f"{error}"
                )

        resultado = st.session_state.get(
            "segmento_cumpleanios"
        )

        if resultado:
            r1, r2, r3 = st.columns(3)

            r1.metric(
                "Cumpleaños encontrados",
                resultado["encontrados"],
            )

            r2.metric(
                "Listos para exportar",
                resultado["exportados"],
            )

            r3.metric(
                "Omitidos sin DNI o email",
                resultado["omitidos"],
            )

            st.caption(
                "Formato de salida: "
                "DNI | NOMBRE | EMAIL"
            )

            st.dataframe(
                resultado["segmento"],
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "⬇️ Descargar archivo para Grido",
                data=resultado["excel"],
                file_name=resultado[
                    "nombre_archivo"
                ],
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True,
                key="descargar_segmento_cumpleanios",
            )

elif modulo == "🤖 IA":

    st.info("Módulo en desarrollo.")

elif modulo == "⚙️ Configuración":

    st.info("Módulo en desarrollo.")
