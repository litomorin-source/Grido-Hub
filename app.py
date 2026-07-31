import importlib

import pandas as pd
import streamlit as st

import modules.socios as socios

importlib.reload(socios)

st.set_page_config(
    page_title="Grido Hub",
    page_icon="🍦",
    layout="wide"
)

st.sidebar.title("Grido Hub")

modulo = st.sidebar.radio(
    "Módulos",
    [
        "🏠 Inicio",
        "👥 Socios",
        "📢 Marketing",
        "🤖 IA",
        "⚙️ Configuración"
    ]
)

st.title("🍦 Grido Hub")
st.caption("Versión 0.1.0")

if modulo == "🏠 Inicio":

    st.success("Proyecto inicializado correctamente.")
    st.subheader("Estado")
    st.info("La base se crea automáticamente al cargar Favoritos por primera vez.")

elif modulo == "👥 Socios":

    st.header("👥 Socios")

    favoritos = st.file_uploader(
        "Favoritos del Club Grido",
        type=["csv", "xlsx"]
    )

    col1, col2 = st.columns(2)

    with col1:
        actualizar = st.button(
            "🔄 Actualizar Base",
            use_container_width=True
        )

    with col2:
        st.button(
            "🆔 Obtener DNI",
            use_container_width=True,
            disabled=True
        )

    st.divider()
    st.subheader("Resumen")

    socios_total = "-"
    nuevos = "-"
    pendientes = "-"
    whatsapp = "-"

    if actualizar:

        if favoritos is None:
            st.warning("Primero seleccioná el archivo Favoritos.")

        else:
            try:
                if favoritos.name.lower().endswith(".csv"):

                    try:
                        df_favoritos = pd.read_csv(
                            favoritos,
                            sep=";",
                            engine="python"
                        )

                        if len(df_favoritos.columns) == 1:
                            raise ValueError("Separador incorrecto")

                    except Exception:
                        favoritos.seek(0)

                        df_favoritos = pd.read_csv(
                            favoritos,
                            sep=",",
                            engine="python"
                        )

                else:
                    df_favoritos = pd.read_excel(favoritos)

                resultado = socios.actualizar_base(df_favoritos)

                socios_total = resultado["socios"]
                nuevos = resultado["nuevos"]
                pendientes = resultado["pendientes_dni"]

                st.success("Base actualizada correctamente.")

            except Exception as error:
                st.error(f"No se pudo actualizar la base: {error}")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Socios", socios_total)
    c2.metric("Nuevos", nuevos)
    c3.metric("Pendientes DNI", pendientes)
    c4.metric("WhatsApp", whatsapp)

else:

    st.info("Módulo en desarrollo.")