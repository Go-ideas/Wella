from __future__ import annotations

import streamlit as st

from journey_model_slide import build_journey_model_pptx, journey_slide_html


st.set_page_config(
    page_title="Modelo Journey | Wella",
    page_icon="🧭",
    layout="wide",
)

st.title("Modelo Journey de decisión de compra")
st.caption(
    "Slide explicativo para clientes: resume cómo funciona la Red Bayesiana Secuencial y cómo interpretar los porcentajes."
)

left, right = st.columns([1, 1])
with left:
    show_slide = st.button("Ver slide explicativo", type="primary", use_container_width=True)
with right:
    pptx_bytes = build_journey_model_pptx()
    st.download_button(
        "Exportar slide a PowerPoint",
        data=pptx_bytes,
        file_name="Wella_Modelo_Journey_Bayesiano.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        use_container_width=True,
    )

if show_slide or st.session_state.get("show_journey_model_slide", False):
    st.session_state["show_journey_model_slide"] = True
    st.markdown(journey_slide_html(), unsafe_allow_html=True)
else:
    with st.expander("Vista previa rápida", expanded=True):
        st.markdown(journey_slide_html(), unsafe_allow_html=True)

st.info(
    "La lámina está pensada para explicar el modelo sin tecnicismos: qué mide, cómo leer los porcentajes, cómo se evalúa la certeza y para qué sirve en negocio."
)
