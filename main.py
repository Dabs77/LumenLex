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
    generate_pdf,
)

def main():
    st.set_page_config(page_title="LumenLex Simplificador", layout="wide")
    st.title("🖋️ LumenLex - Simplificación de Contratos")

    uploaded = st.file_uploader(
        "Sube tu contrato (.docx o .pdf)", type=["docx", "pdf"]
    )
    if not uploaded:
        return

    # Paso 1: Extraer texto inmediatamente y mostrar área de texto
    if 'extracted_text' not in st.session_state:
        with st.spinner("Extrayendo texto del documento..."):
            raw = extract_raw_text(uploaded.name, uploaded.getvalue())
            st.session_state.extracted_text = raw
    else:
        raw = st.session_state.extracted_text

    st.subheader("Texto extraído:")
    st.text_area("", raw, height=200)

    # Paso 2: Botón para simplificar
    if st.button("🚀 Simplificar Contrato"):
        try:
            with st.spinner("Simplificando con Gemini..."):
                result = simplify_contract(raw)
            html = generate_html(result, uploaded.name)

            st.header("✅ Vista HTML")
            components.html(html, height=600)

            st.header("📥 Descargas")
            st.download_button(
                "Descargar JSON",
                data=json.dumps(result, indent=2, ensure_ascii=False),
                file_name=f"simplificado_{uploaded.name}.json",
                mime="application/json"
            )
            st.download_button(
                "Descargar HTML",
                data=html,
                file_name=f"simplificado_{uploaded.name}.html",
                mime="text/html"
            )

            pdf_bytes = generate_pdf(result)
            st.download_button(
                "Descargar PDF",
                data=pdf_bytes,
                file_name=f"simplificado_{uploaded.name}.pdf",
                mime="application/pdf"
            )

        except Exception as e:
            st.error(f"❌ Error: {e}")

if __name__ == "__main__":
    main()



