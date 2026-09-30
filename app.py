from __future__ import annotations

import gc
import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from engine import (
    InvalidDatabase,
    FILTER_COLUMNS,
    options_for,
    load_database_connection,
    apply_filters,
    base_quality,
    executive_kpis,
    decision_stage_summary,
    top_routes,
    tree_links,
    maxdiff_compare,
    substitution_kpis,
    scenario_counts,
    shelf_priority,
    shelf_pair_score,
    friction_summary,
)
from secure_io import EncryptedPackageError, decrypt_sqlite_bytes, package_fingerprint, sqlite_connection_from_bytes

st.set_page_config(page_title="Wella | Decision Simulator", page_icon="🎯", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1500px;}
[data-testid="stMetric"] {background: #F7F9FC; border: 1px solid #E3E8EF; padding: 12px; border-radius: 14px;}
.small-note {font-size: .82rem; color: #667085;}
.hero {padding: 15px 18px; border-radius: 16px; background: linear-gradient(135deg,#071A33,#123C66); color:white; margin-bottom:10px;}
.hero h2 {margin:0; font-size:1.55rem;}
.hero p {margin:4px 0 0 0; opacity:.88;}
.secure {padding:10px 14px; border:1px solid #C7D7EA; background:#F6FAFF; border-radius:12px; margin:.3rem 0 .8rem 0;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero"><h2>Wella · Decision Simulator</h2>'
    '<p>El sitio no contiene datos del estudio. El cliente carga un archivo cifrado y el análisis se procesa en memoria durante su sesión.</p></div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="secure"><b>Privacidad por diseño:</b> no existe base precargada, no se incluye información en GitHub y no se escribe la base descifrada al disco del servidor.</div>',
    unsafe_allow_html=True,
)


def clear_loaded_data() -> None:
    for key in ["dataset", "metadata", "package_fp", "loaded_name", "db_password"]:
        if key in st.session_state:
            del st.session_state[key]
    gc.collect()


uploaded = st.file_uploader(
    "1. Carga el archivo cifrado del estudio (.goideas)",
    type=["goideas"],
    help="El archivo debe haber sido generado por Go Ideas. El sitio no acepta bases .db/.sav en claro.",
)

if uploaded is None:
    if "dataset" in st.session_state:
        clear_loaded_data()
    st.info("Carga el archivo **.goideas** entregado por Go Ideas. Sin ese archivo, el reporteador no contiene ni puede reconstruir datos del estudio.")
    st.caption("Streamlit recibe el archivo en el backend durante la sesión. El paquete viaja cifrado; la clave se introduce por separado y la base se descifra únicamente en memoria.")
    st.stop()

package_bytes = uploaded.getvalue()
fp = package_fingerprint(package_bytes)

if st.session_state.get("package_fp") != fp:
    # A newly selected encrypted package invalidates any previous in-memory dataset.
    clear_loaded_data()

if "dataset" not in st.session_state:
    with st.form("unlock_form", clear_on_submit=True):
        password = st.text_input("2. Clave del archivo", type="password", key="db_password")
        unlock = st.form_submit_button("Abrir reporteador", type="primary", use_container_width=True)

    if not unlock:
        st.stop()

    try:
        plaintext_db = decrypt_sqlite_bytes(package_bytes, password)
        con = sqlite_connection_from_bytes(plaintext_db)
        try:
            df, meta = load_database_connection(con)
        finally:
            con.close()
        # Drop plaintext byte buffer as early as possible.
        del plaintext_db
        gc.collect()
        st.session_state["dataset"] = df
        st.session_state["metadata"] = meta
        st.session_state["package_fp"] = fp
        st.session_state["loaded_name"] = uploaded.name
        st.session_state["db_password"] = ""
        st.rerun()
    except (EncryptedPackageError, InvalidDatabase) as exc:
        st.error(str(exc))
        st.stop()
    except Exception:
        st.error("No fue posible abrir el archivo. Verifica que sea el paquete correcto y vuelve a intentarlo.")
        st.stop()

# From here on, only the analytical dataframe and metadata live in session memory.
df = st.session_state["dataset"]
meta = st.session_state["metadata"]

with st.sidebar:
    st.success("Archivo seguro abierto")
    st.caption(st.session_state.get("loaded_name", "Archivo cifrado"))
    if st.button("Cerrar sesión y borrar datos de memoria", use_container_width=True):
        clear_loaded_data()
        st.rerun()
    st.divider()
    st.markdown("### Filtros")

filters = {}
filter_labels = {
    "producto": "Producto",
    "marca": "Marca",
    "cadena": "Cadena",
    "edad_rango": "Edad",
    "area_nielsen": "Área Nielsen",
    "nse": "NSE",
    "sexo": "Sexo",
}
for col in FILTER_COLUMNS:
    opts = options_for(df, col)
    filters[col] = st.sidebar.multiselect(filter_labels.get(col, col), opts, default=[])

filtered = apply_filters(df, filters)
n = len(filtered)
quality, quality_note = base_quality(n)
st.sidebar.markdown(f"**Base actual:** n={n}")
st.sidebar.caption(f"{quality} · {quality_note}")

if n == 0:
    st.warning("La combinación de filtros no contiene entrevistas.")
    st.stop()

if n < 30:
    st.error("Base menor a 30. La vista queda bloqueada para evitar sobreinterpretación de porcentajes o simulaciones.")
    st.stop()

page = st.radio(
    "Vista",
    ["Resumen", "Árbol de decisión", "Drivers MaxDiff", "Simulador de sustitución", "Anaquel"],
    horizontal=True,
)

if page == "Resumen":
    k = executive_kpis(filtered)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Base", f"{n}", quality)
    c2.metric("Valida el árbol", f"{k['validacion_arbol']:.1f}%")
    c3.metric("Primer gate", k["primer_gate"] or "—")
    c4.metric("Top driver MaxDiff", k["top_driver"] or "—")
    c5, c6, c7 = st.columns(3)
    c5.metric("Cambia de marca si falta su marca", f"{k['cambia_marca_si_falta_marca']:.1f}%")
    c6.metric("Cambia de marca para conservar tono", f"{k['cambia_marca_para_conservar_tono']:.1f}%")
    c7.metric("Compra aun sin promoción", f"{k['compra_sin_promocion']:.1f}%")

    stage = decision_stage_summary(filtered)
    fig = px.bar(
        stage,
        x="pct",
        y="criterio",
        color="etapa",
        barmode="group",
        orientation="h",
        labels={"pct": "%", "criterio": "Criterio", "etapa": "Etapa"},
        title="Qué entra primero, después y al cierre",
    )
    fig.update_layout(height=520, legend_title_text="", yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

    routes = top_routes(filtered, 8)
    st.markdown("#### Rutas más frecuentes")
    st.dataframe(routes.style.format({"pct": "{:.1f}%"}), use_container_width=True, hide_index=True)

elif page == "Árbol de decisión":
    choices = ["Todos"] + options_for(filtered, "decision_1")
    sel = st.selectbox("Explorar desde el primer criterio", choices, index=0)
    depth = st.slider("Detalle de ramas", 2, 6, 4, help="Controla cuántas ramas se muestran para mantener el árbol legible.")
    links = tree_links(filtered, None if sel == "Todos" else sel, top_d2=depth, top_d3=max(2, depth - 1))
    if not links["labels"]:
        st.warning("No hay datos para esa ruta.")
    else:
        fig = go.Figure(
            go.Sankey(
                arrangement="snap",
                node=dict(label=links["labels"], pad=18, thickness=18),
                link=dict(
                    source=links["source"],
                    target=links["target"],
                    value=links["value"],
                    customdata=links["custom"],
                    hovertemplate="%{source.label} → %{target.label}<br>%{customdata}<extra></extra>",
                ),
            )
        )
        fig.update_layout(title="Árbol dinámico D1 → D2 → D3", height=690, font_size=12)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Los porcentajes del árbol son condicionales a la rama anterior; no representan causalidad.")
    st.markdown("#### Top rutas completas")
    st.dataframe(top_routes(filtered, 12).style.format({"pct": "{:.1f}%"}), use_container_width=True, hide_index=True)

elif page == "Drivers MaxDiff":
    comp = maxdiff_compare(filtered, df)
    show_total = st.toggle("Comparar contra total", value=True)
    if show_total:
        plot = comp.melt(id_vars=["driver"], value_vars=["segmento", "total"], var_name="serie", value_name="score")
        plot["serie"] = plot["serie"].map({"segmento": "Segmento filtrado", "total": "Total"})
        fig = px.bar(plot, x="score", y="driver", color="serie", barmode="group", orientation="h", title="Importancia MaxDiff")
    else:
        fig = px.bar(comp, x="segmento", y="driver", orientation="h", title="Importancia MaxDiff del segmento")
    fig.update_layout(height=560, yaxis={"categoryorder": "total ascending"}, legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        comp[["driver", "segmento", "total", "delta"]].style.format({"segmento": "{:.2f}", "total": "{:.2f}", "delta": "{:+.2f}"}),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("Los scores son utilidades HB reescaladas; describen importancia relativa dentro del conjunto de atributos evaluados.")

elif page == "Simulador de sustitución":
    k = substitution_kpis(filtered)
    a, b, c = st.columns(3)
    a.metric("Riesgo de cambio de marca", f"{k['cambia_marca_si_falta_marca']:.1f}%", help="Declara comprar otra marca si la marca buscada no está disponible.")
    b.metric("Tono domina a marca", f"{k['cambia_marca_para_conservar_tono']:.1f}%", help="Declara cambiar de marca para conservar el tono deseado.")
    c.metric("Resistencia a perder promoción", f"{k['compra_sin_promocion']:.1f}%", help="Declara comprar de todos modos sin promoción.")

    scenario = st.selectbox("Escenario", ["Marca no disponible", "Tono/color no disponible", "Sin promoción"])
    sim_n = st.slider("Compradores hipotéticos", 100, 5000, 1000, 100)
    t = scenario_counts(filtered, scenario, sim_n)
    fig = px.bar(t, x="pct", y="respuesta", orientation="h", text="esperados", title=f"Qué harían {sim_n:,} compradores con el patrón observado")
    fig.update_traces(texttemplate="%{text} compradores", textposition="outside")
    fig.update_layout(height=470, yaxis={"categoryorder": "total ascending"}, xaxis_title="% observado")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Simulación de escala: aplica las proporciones declaradas observadas al número hipotético. No es un pronóstico causal de ventas.")

elif page == "Anaquel":
    priority = shelf_priority(filtered)
    fig = px.bar(
        priority,
        x="indice_prioridad",
        y="organizacion",
        orientation="h",
        title="Prioridad declarada para organizar/encontrar producto",
        labels={"indice_prioridad": "Índice 2:1 (primera vs segunda ayuda)", "organizacion": ""},
    )
    fig.update_layout(height=460, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

    opts = priority["organizacion"].tolist()
    left, right = st.columns(2)
    primary = left.selectbox("Organización principal", opts, index=0)
    sec_opts = [x for x in opts if x != primary]
    secondary = right.selectbox("Organización secundaria", sec_opts, index=0)
    pair = shelf_pair_score(filtered, primary, secondary)
    x, y, z = st.columns(3)
    x.metric("Coincidencia exacta", f"{pair['exact_order']:.1f}%")
    y.metric("Par en Top 2", f"{pair['top2_any_order']:.1f}%")
    z.metric("Cobertura del par", f"{pair['coverage']:.1f}%")
    easy, barriers = friction_summary(filtered)
    st.markdown(f"**{easy:.1f}%** declara que encontrar el producto fue fácil o muy fácil.")
    if len(barriers):
        fig2 = px.bar(barriers, x="pct", y="barrera", orientation="h", title="Barreras entre quienes no tuvieron una experiencia claramente fácil")
        fig2.update_layout(height=380, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig2, use_container_width=True)
    st.caption("El simulador de anaquel mide afinidad declarada con formas de organización; no estima incremento causal de ventas.")

st.divider()
st.caption(f"{meta.get('project_name', 'Proyecto')} · Schema {meta.get('schema_version', '—')} · Datos descifrados y procesados únicamente en memoria de sesión.")
