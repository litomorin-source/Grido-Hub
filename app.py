
import streamlit as st

st.set_page_config(page_title="Grido Hub", page_icon="🍦", layout="wide")

st.sidebar.title("Grido Hub")
mod = st.sidebar.radio("Módulos", ["🏠 Inicio","👥 Socios","📢 Marketing","🤖 IA","⚙️ Configuración"])

st.title("🍦 Grido Hub")
st.caption("Versión 0.1.0")

if mod=="🏠 Inicio":
    st.success("Proyecto inicializado correctamente.")
    st.subheader("Estado")
    st.info("Sin base cargada.")
elif mod=="👥 Socios":
    st.header("Socios")
    st.button("Actualizar base")
    st.button("🆔 Obtener DNI")
    st.info("Módulo en construcción (GH-002).")
else:
    st.info("Módulo en desarrollo.")
