"""
main.py
Interfaz Streamlit para LumenLex con persistencia de estado para evitar reset tras descargas.
"""
import json
import streamlit as st
import streamlit.components.v1 as components

from functions import (
    extract_raw_text,
    simplify_contract,
    generate_html,
    generate_pdf_from_html,
)

# Claves para session_state
RAW_KEY = 'raw_text'
DATA_KEY = 'simplified_data'
HTML_KEY = 'simplified_html'


def main():
    st.set_page_config(page_title="LumenLex Simplificador", layout="wide")
    st.title("🖋️ LumenLex - Simplificación de Contratos")

    # Cargar archivo
    uploaded = st.file_uploader("Sube tu contrato (.docx o .pdf)", type=["docx", "pdf"])
    if not uploaded:
        # Si no hay archivo, limpiamos estado
        for key in (RAW_KEY, DATA_KEY, HTML_KEY):
            if key in st.session_state:
                del st.session_state[key]
        return

    # Extraer texto al subir
    if RAW_KEY not in st.session_state:
        with st.spinner("Extrayendo texto..."):
            raw = extract_raw_text(uploaded.name, uploaded.getvalue())
            st.session_state[RAW_KEY] = raw
    raw = st.session_state[RAW_KEY]

    # Mostrar texto extraído
    st.subheader("Texto extraído:")
    st.text_area("", raw, height=200)

    # Si aún no se simplificó, mostrar botón
    if DATA_KEY not in st.session_state:
        if st.button("🚀 Simplificar Contrato"):
            try:
                with st.spinner("Simplificando con Gemini..."):
                    data = simplify_contract(raw)
                # Generar HTML desde datos
                html = generate_html(data, uploaded.name)
                # Guardamos en session_state
                st.session_state[DATA_KEY] = data
                st.session_state[HTML_KEY] = html
            except Exception as e:
                st.error(f"❌ Error durante la simplificación: {e}")
    
    # Si ya se simplificó, mostrar resultados y descargas
    if DATA_KEY in st.session_state and HTML_KEY in st.session_state:
        data = st.session_state[DATA_KEY]
        html = st.session_state[HTML_KEY]

        st.header("✅ Vista HTML")
        components.html(html, height=800, scrolling=True)

        st.header("📥 Descargas")
        # JSON
        st.download_button(
            label="Descargar JSON",
            data=json.dumps(data, indent=2, ensure_ascii=False),
            file_name=f"simplificado_{uploaded.name}.json",
            mime="application/json"
        )
        # HTML
        st.download_button(
            label="Descargar HTML",
            data=html,
            file_name=f"simplificado_{uploaded.name}.html",
            mime="text/html"
        )
        # PDF
        try:
            pdf_bytes = generate_pdf_from_html(html)
            st.download_button(
                label="Descargar PDF",
                data=pdf_bytes,
                file_name=f"simplificado_{uploaded.name}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"❌ Error generando PDF: {e}")

if __name__ == "__main__":
    main()


