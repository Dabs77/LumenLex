"""
main.py
Interfaz Streamlit para LumenLex.
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

def main():
    st.set_page_config(page_title="LumenLex Simplificador", layout="wide")
    st.title("🖋️ LumenLex - Simplificación de Contratos")

    uploaded = st.file_uploader("Sube tu contrato (.docx o .pdf)", type=["docx", "pdf"])
    if not uploaded:
        return

    # Extraer texto en session_state
    if 'extracted_text' not in st.session_state:
        with st.spinner("Extrayendo texto..."):
            raw = extract_raw_text(uploaded.name, uploaded.getvalue())
            st.session_state.extracted_text = raw
    raw = st.session_state.extracted_text

    st.subheader("Texto extraído:")
    st.text_area("", raw, height=200)

    if st.button("🚀 Simplificar Contrato"):
        try:
            with st.spinner("Simplificando con Gemini..."):
                data = simplify_contract(raw)

            html = generate_html(data, uploaded.name)
            st.header("✅ Vista HTML")
            components.html(html, height=800, scrolling=True)

            st.header("📥 Descargas")
            st.download_button(
                "Descargar JSON", json.dumps(data, indent=2, ensure_ascii=False),
                file_name=f"simplificado_{uploaded.name}.json",
                mime="application/json"
            )
            st.download_button(
                "Descargar HTML", html,
                file_name=f"simplificado_{uploaded.name}.html",
                mime="text/html"
            )

            # PDF desde HTML
            pdf_bytes = generate_pdf_from_html(html)
            st.download_button(
                "Descargar PDF", pdf_bytes,
                file_name=f"simplificado_{uploaded.name}_export.pdf",
                mime="application/pdf"
            )

        except Exception as e:
            st.error(f"❌ Error: {e}")

if __name__ == "__main__":
    main()




