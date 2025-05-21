import json
import streamlit as st
import streamlit.components.v1 as components
from functions import (
    extract_raw_text,
    simplify_contract,
    generate_html,
    generate_pdf_from_html,
    # agregamos esta función para la edición por sección:
    refine_section_with_instruction,
    refine_all_sections_with_instruction
)

RAW_KEY = 'raw_text'
DATA_KEY = 'simplified_data'
HTML_KEY = 'simplified_html'
PDF_KEY = 'pdf_bytes'
UPLOADED_NAME_KEY = 'uploaded_name'


def regenerate_outputs():
    data = st.session_state[DATA_KEY]
    uploaded_name = st.session_state[UPLOADED_NAME_KEY]
    html = generate_html(data, uploaded_name)
    st.session_state[HTML_KEY] = html
    st.session_state[PDF_KEY] = generate_pdf_from_html(html)


def main():
    st.set_page_config(page_title="LumenLex Simplificador", layout="wide", initial_sidebar_state="auto")
    # Forzar tema claro
    st.markdown(
        """
        <style>
        body, .stApp, .st-cq, .st-cv, .st-cw, .st-cx, .st-cy, .st-cz, .st-da, .st-db, .st-dc, .st-dd, .st-de, .st-df, .st-dg, .st-dh, .st-di, .st-dj, .st-dk, .st-dl, .st-dm, .st-dn, .st-do, .st-dp, .st-dq, .st-dr, .st-ds, .st-dt, .st-du, .st-dv, .st-dw, .st-dx, .st-dy, .st-dz, .st-e0, .st-e1, .st-e2, .st-e3, .st-e4, .st-e5, .st-e6, .st-e7, .st-e8, .st-e9, .st-ea, .st-eb, .st-ec, .st-ed, .st-ee, .st-ef, .st-eg, .st-eh, .st-ei, .st-ej, .st-ek, .st-el, .st-em, .st-en, .st-eo, .st-ep, .st-eq, .st-er, .st-es, .st-et, .st-eu, .st-ev, .st-ew, .st-ex, .st-ey, .st-ez {
            background-color: #fff !important;
            color: #222 !important;
        }
        [data-testid="stHeader"], [data-testid="stSidebar"], .st-emotion-cache-1avcm0n {
            background-color: #fff !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.title("🖋️ LumenLex - Simplificación de Contratos")

    uploaded = st.file_uploader("Sube tu contrato (.docx o .pdf)", type=["docx", "pdf"])
    if not uploaded:
        for key in (RAW_KEY, DATA_KEY, HTML_KEY, PDF_KEY, UPLOADED_NAME_KEY):
            if key in st.session_state:
                del st.session_state[key]
        return

    st.session_state[UPLOADED_NAME_KEY] = uploaded.name

    if RAW_KEY not in st.session_state:
        with st.spinner("Extrayendo texto..."):
            raw = extract_raw_text(uploaded.name, uploaded.getvalue())
            st.session_state[RAW_KEY] = raw

    raw = st.session_state[RAW_KEY]
    st.subheader("Texto extraído:")
    st.text_area("", raw, height=200)

    if DATA_KEY not in st.session_state:
        if st.button("🚀 Simplificar Contrato"):
            try:
                with st.spinner("Simplificando con Gemini..."):
                    data = simplify_contract(raw)
                html = generate_html(data, uploaded.name)
                pdf_bytes = generate_pdf_from_html(html)
                st.session_state[DATA_KEY] = data
                st.session_state[HTML_KEY] = html
                st.session_state[PDF_KEY] = pdf_bytes
            except Exception as e:
                st.error(f"❌ Error durante la simplificación: {e}")

    if DATA_KEY in st.session_state:
        data = st.session_state[DATA_KEY]

        st.header("✅ Secciones simplificadas con edición individual")

        # NUEVO: Edición global de todas las secciones
        st.subheader("✏️ Edición global de todas las secciones")
        global_instruction = st.text_input(
            label="¿Qué cambio quieres aplicar a TODO el contrato simplificado? (Ejemplo: 'Haz todo el texto más formal', 'Hazlo más breve', 'Hazlo más claro para personas sin formación legal')",
            key="global_instruction_input"
        )
        if st.button("Refinar TODO el contrato", key="refine_all_btn"):
            if not global_instruction.strip():
                st.warning("Por favor ingresa una instrucción global para refinar el contrato.")
            else:
                with st.spinner("Refinando TODO el contrato con Gemini..."):
                    new_data = refine_all_sections_with_instruction(data, global_instruction)
                    st.session_state[DATA_KEY] = new_data
                    regenerate_outputs()
                    st.success("¡Contrato completo refinado y actualizado!")
                data = st.session_state[DATA_KEY]  # actualizar variable local

        for i, sec in enumerate(data['sections']):
            st.subheader(f"Cláusula {i+1}: {sec['section_title']}")

            # Input + botón ARRIBA
            inst_key = f"instruction_section_{i}"
            instruction = st.text_input(
                label=f"¿Qué quieres que haga Gemini con esta sección? (Ejemplo: 'Hazlo más formal, agrega lista con viñetas')",
                key=inst_key
            )

            if st.button(f"Refinar sección {i+1}", key=f"refine_section_btn_{i}"):
                if not instruction.strip():
                    st.warning("Por favor ingresa una instrucción para refinar la sección.")
                else:
                    with st.spinner("Refinando sección con Gemini..."):
                        refined_section = refine_section_with_instruction(sec, instruction)
                        st.session_state[DATA_KEY]['sections'][i] = refined_section
                        regenerate_outputs()
                        st.success("Sección refinada y actualizada!")
                    sec = refined_section  # actualizar variable local para mostrar el nuevo texto

            # Contenedor para mostrar el texto SIMPLIFICADO justo debajo del input
            section_display = st.empty()
            paras = [p.strip() for p in sec['simplified_text'].split('\n') if p.strip()]
            display_text = "\n\n".join(paras)
            section_display.markdown(display_text)

            st.markdown(f"*Justificación:* _{sec['justification']}_")
            st.markdown("---")

        st.header("🌐 Vista HTML actualizada")
        components.html(st.session_state[HTML_KEY], height=800, scrolling=True)

        st.header("📥 Descargas")
        st.download_button(
            "Descargar JSON",
            data=json.dumps(st.session_state[DATA_KEY], indent=2, ensure_ascii=False),
            file_name=f"simplificado_{st.session_state[UPLOADED_NAME_KEY]}.json",
            mime="application/json"
        )
        st.download_button(
            "Descargar HTML",
            data=st.session_state[HTML_KEY],
            file_name=f"simplificado_{st.session_state[UPLOADED_NAME_KEY]}.html",
            mime="text/html"
        )
        st.download_button(
            "Descargar PDF",
            data=st.session_state[PDF_KEY],
            file_name=f"simplificado_{st.session_state[UPLOADED_NAME_KEY]}.pdf",
            mime="application/pdf"
        )




if __name__ == "__main__":
    main()



