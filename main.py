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
    refine_all_sections_with_instruction,
    contract_to_visualization_json,
    render_timeline,
    render_comparison,
    render_hierarchy,
    render_relation,
    render_geography,
    general_restructure_contract
)

RAW_KEY = 'raw_text'
DATA_KEY = 'simplified_data'
HTML_KEY = 'simplified_html'
PDF_KEY = 'pdf_bytes'
UPLOADED_NAME_KEY = 'uploaded_name'
PAGES = ["Simplificación", "Visualización Gráfica"]


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

    page = st.sidebar.radio("Navegación", PAGES)
    if page == "Simplificación":
        simplification_page()
    elif page == "Visualización Gráfica":
        visualization_page()


def simplification_page():
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

        # CAMPO ÚNICO: Modificación general del documento simplificado
        st.subheader("🛠️ Modificación general del documento simplificado")
        general_instruction = st.text_area(
            label="¿Qué cambio general quieres aplicar al documento simplificado? (Ejemplo: 'Fusiona las cláusulas 2 y 3', 'Haz todo el texto más claro', 'Elimina la cláusula de penalidad', etc.)",
            key="general_instruction_input"
        )
        if st.button("Aplicar modificación general", key="general_modification_btn"):
            if not general_instruction.strip():
                st.warning("Por favor ingresa una instrucción para modificar el documento.")
            else:
                with st.spinner("Modificando el documento con Gemini..."):
                    try:
                        new_data = general_restructure_contract(
                            text=raw,
                            instruction=general_instruction,
                            response=json.dumps(data, ensure_ascii=False)
                        )
                        st.session_state[DATA_KEY] = new_data
                        regenerate_outputs()
                        st.success("¡Documento modificado y actualizado!")
                        data = st.session_state[DATA_KEY]
                    except Exception as e:
                        st.error(f"❌ Error durante la modificación: {e}")

        for i, sec in enumerate(data['sections']):
            st.subheader(f"{sec['section_title']}")

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
        st.markdown("---")
        st.markdown("### ¿Quieres ver una visualización gráfica del contrato?")
        if st.button("Ir a Visualización Gráfica"):
            st.session_state['go_to_visualization'] = True
            st.experimental_rerun()


def visualization_page():
    st.title("📊 Visualización Gráfica del Contrato")
    raw = st.session_state.get('raw_text', None)
    if not raw:
        st.warning("Primero debes subir y procesar un contrato en la página de Simplificación.")
        return
    if st.button("Generar visualización gráfica con Gemini"):
        with st.spinner("Consultando Gemini y generando visualización..."):
            data = contract_to_visualization_json(raw)
            st.session_state['visualization_data'] = data
    data = st.session_state.get('visualization_data', None)
    if data:
        st.subheader(f"Tipo de visualización: {data['category']}")
        params = data['parameters']
        if data['category'] == 'tiempo':
            fig = render_timeline(params)
            st.plotly_chart(fig, use_container_width=True)
        elif data['category'] == 'comparación':
            fig = render_comparison(params)
            st.plotly_chart(fig, use_container_width=True)
        elif data['category'] == 'jerarquía':
            src = render_hierarchy(params)
            st.graphviz_chart(src)
        elif data['category'] == 'relación':
            fig = render_relation(params)
            st.pyplot(fig)
        elif data['category'] == 'geografía':
            fig = render_geography(params)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Tipo de visualización no soportado para renderizado automático.")


if __name__ == "__main__":
    main()



