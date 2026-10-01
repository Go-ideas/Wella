from __future__ import annotations

import gc
import html
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
from tendential import (
    tendential_eligible,
    tendential_kpis,
    decision_stage_tendential,
    tree_links_tendential,
    maxdiff_tendential,
    substitution_tendential,
    shelf_priority_tendential,
    shelf_pair_tendential,
    friction_tendential,
)

st.set_page_config(page_title="Wella | Decision Simulator", page_icon="🎯", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1500px;}
[data-testid="stMetric"] {background: #F7F9FC; border: 1px solid #E3E8EF; padding: 12px; border-radius: 14px;}
.small-note {font-size: .82rem; color: #667085;}
.hero {padding: 18px 20px; border-radius: 18px; background: linear-gradient(135deg,#071A33,#123C66); color:white; margin-bottom:12px;}
.hero h2 {margin:0; font-size:1.65rem;}
.hero p {margin:6px 0 0 0; opacity:.90; font-size:1rem;}
.secure {padding:10px 14px; border:1px solid #C7D7EA; background:#F6FAFF; border-radius:12px; margin:.3rem 0 .8rem 0;}
[data-testid="stMetricValue"] {font-size:1.65rem;}
[data-testid="stMetricLabel"] {font-weight:600;}
.kpi-card {
    background:#F7F9FC;
    border:1px solid #E3E8EF;
    border-radius:18px;
    padding:18px 20px;
    min-height:138px;
    display:flex;
    flex-direction:column;
    justify-content:space-between;
}
.kpi-label {
    color:#21324A;
    font-size:0.98rem;
    line-height:1.25;
    font-weight:600;
    margin-bottom:10px;
    white-space:normal;
    overflow-wrap:anywhere;
}
.kpi-value {
    color:#12243B;
    font-size:1.82rem;
    line-height:1.12;
    font-weight:500;
    white-space:normal;
    overflow-wrap:anywhere;
    word-break:normal;
}
.kpi-note {
    display:inline-block;
    margin-top:10px;
    font-size:0.82rem;
    line-height:1.2;
    color:#245E45;
    background:#E7F4EC;
    padding:4px 9px;
    border-radius:999px;
    width:max-content;
    max-width:100%;
}
.base-strip {
    display:flex;
    align-items:center;
    gap:10px;
    flex-wrap:wrap;
    margin:4px 0 18px 0;
    color:#506176;
    font-size:.92rem;
}
.base-pill {
    display:inline-flex;
    align-items:center;
    gap:6px;
    padding:6px 11px;
    border-radius:999px;
    background:#EEF4FA;
    color:#183B5B;
    font-weight:600;
}
.flow-wrap {
    display:grid;
    grid-template-columns:1fr 42px 1fr 42px 1fr;
    align-items:stretch;
    gap:8px;
    margin:6px 0 22px 0;
}
.flow-step {
    border:1px solid #DCE5EE;
    border-radius:18px;
    padding:18px 20px;
    background:#FBFCFE;
    min-height:150px;
}
.flow-kicker {
    color:#65758A;
    font-size:.82rem;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:.03em;
    margin-bottom:10px;
}
.flow-value {
    color:#102A43;
    font-size:1.55rem;
    line-height:1.18;
    font-weight:600;
    overflow-wrap:anywhere;
}
.flow-note {
    color:#667085;
    font-size:.88rem;
    line-height:1.35;
    margin-top:10px;
}
.flow-arrow {
    display:flex;
    align-items:center;
    justify-content:center;
    color:#8BA1B8;
    font-size:1.8rem;
    font-weight:300;
}
@media (max-width: 900px) {
    .flow-wrap {grid-template-columns:1fr; gap:8px;}
    .flow-arrow {transform:rotate(90deg); min-height:24px;}
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero"><h2>Wella · Explorador de decisión de compra</h2>'
    '<p>Carga el archivo seguro y explora cómo deciden los compradores, qué pesa más en la elección y qué pasa cuando una opción no está disponible.</p></div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="secure"><b>Tu información permanece separada del sitio:</b> el reporteador no trae una base precargada. Los resultados aparecen únicamente después de cargar el archivo seguro del estudio.</div>',
    unsafe_allow_html=True,
)


def clear_loaded_data() -> None:
    for key in ["dataset", "metadata", "package_fp", "loaded_name", "unlock_password"]:
        if key in st.session_state:
            del st.session_state[key]
    gc.collect()


def polish_bar(fig, height=480, percent_axis=False):
    """Ajustes visuales comunes para gráficos de barras."""
    fig.update_traces(textfont_size=13, cliponaxis=False, marker_line_width=0)
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=55, t=70, b=25),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(size=13),
        legend_title_text="",
        xaxis=dict(
            showgrid=True,
            gridcolor="#E8EDF3",
            zeroline=False,
            ticksuffix="%" if percent_axis else "",
        ),
        yaxis=dict(title=""),
    )
    return fig


def kpi_card(label: str, value: str, note: str | None = None):
    """Tarjeta KPI con texto completo, sin truncar valores largos."""
    label_safe = html.escape(str(label))
    value_safe = html.escape(str(value))
    note_html = f'<div class="kpi-note">{html.escape(str(note))}</div>' if note else ""
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label_safe}</div>'
        f'<div class="kpi-value">{value_safe}</div>'
        f'{note_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


uploaded = st.file_uploader(
    "1. Carga el archivo seguro del estudio (.goideas)",
    type=["goideas"],
    help="Usa el archivo .goideas entregado por Go Ideas. El sitio no acepta bases originales en claro.",
)

if uploaded is None:
    if "dataset" in st.session_state:
        clear_loaded_data()
    st.info("Para comenzar, carga el archivo **.goideas** entregado por Go Ideas. Sin ese archivo no se muestran resultados.")
    st.caption("El archivo está protegido y se abre únicamente durante tu sesión.")
    st.stop()

package_bytes = uploaded.getvalue()
fp = package_fingerprint(package_bytes)

if "dataset" in st.session_state and st.session_state.get("package_fp") != fp:
    # Only invalidate an already-loaded dataset when the user selects a different package.
    # Do not clear the password field while the user is still unlocking the first package.
    clear_loaded_data()

if "dataset" not in st.session_state:
    # Keep unlock controls outside a form so stale validation messages disappear
    # as soon as the user edits the password.
    password = st.text_input("2. Clave del archivo", type="password", key="unlock_password")
    unlock = st.button("Abrir reporteador", type="primary", use_container_width=True)

    if not unlock:
        st.caption("Introduce la clave entregada junto con este archivo y después selecciona **Abrir reporteador**.")
        st.stop()

    if len(password) < 10:
        st.error("La clave debe contener al menos 10 caracteres.")
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
        st.rerun()
    except (EncryptedPackageError, InvalidDatabase) as exc:
        st.error(str(exc))
        st.stop()
    except Exception:
        st.error("No fue posible abrir el archivo. Verifica que sea el paquete correcto y vuelve a intentarlo.")
        st.stop()

# From here on, only the analytical dataframe and metadata live in session memory.
# The password is no longer needed after decryption.
st.session_state.pop("unlock_password", None)
df = st.session_state["dataset"]
meta = st.session_state["metadata"]

with st.sidebar:
    st.success("Archivo seguro abierto")
    st.caption(st.session_state.get("loaded_name", "Archivo cifrado"))
    if st.button("Cerrar sesión y borrar datos de memoria", use_container_width=True):
        clear_loaded_data()
        st.rerun()
    st.divider()
    st.markdown("### Filtra la lectura")

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
st.sidebar.markdown(f"**Entrevistas en esta lectura:** {n}")
st.sidebar.caption(f"{quality} · {quality_note}")

if n == 0:
    st.warning("La combinación de filtros no contiene entrevistas.")
    st.stop()

selected_products = filters.get("producto", [])
tendential_available = len(selected_products) == 1 and tendential_eligible(n)
reference = None
reading_mode = "Observada"

if tendential_available:
    ref_filters = dict(filters)
    ref_filters["producto"] = []
    reference = apply_filters(df, ref_filters)
    reference = reference[reference["producto"] != selected_products[0]].copy()
    default_index = 0 if n < 30 else 1
    reading_mode = st.sidebar.radio(
        "Tipo de lectura",
        ["Tendencial", "Observada"],
        index=default_index,
        help="La lectura tendencial ayuda a interpretar productos con pocas entrevistas apoyándose en el comportamiento de la categoría. No crea entrevistas nuevas.",
    )
    st.sidebar.caption("Observada = respuesta directa. Tendencial = lectura apoyada en el patrón de la categoría cuando la base es pequeña.")
elif n < 30:
    st.error("Base menor a 30. Para habilitar lectura tendencial selecciona un solo producto con al menos 10 entrevistas.")
    st.stop()

if n < 10:
    st.error("Base menor a 10. No se genera lectura individual.")
    st.stop()

is_tendential = reading_mode == "Tendencial" and reference is not None and len(reference) > 0

if is_tendential:
    st.info(
        f"**Lectura tendencial · base real n={n}.** "
        "Esta lectura conserva lo observado en el producto y lo contrasta con el patrón de la categoría para evitar cambios exagerados por una base pequeña. "
        "La base real sigue siendo la misma."
    )

page = st.radio(
    "¿Qué quieres explorar?",
    ["Resumen", "Cómo se decide", "Qué pesa más", "Qué pasa si falta...", "Cómo ordenar el anaquel"],
    horizontal=True,
)

if page == "Resumen":
    st.markdown("### Resumen de la compra")
    st.caption("Una lectura rápida de cómo se toma la decisión y qué tan fácil es cambiar de opción.")
    k = tendential_kpis(filtered, reference) if is_tendential else executive_kpis(filtered)

    st.markdown(
        f'<div class="base-strip">'
        f'<span class="base-pill">Base: {n} entrevistas</span>'
        f'<span class="base-pill">{html.escape(str(quality))}</span>'
        f'<span>La secuencia declarada describe la compra para <b>{k["validacion_arbol"]:.1f}%</b> de los entrevistados.</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    first_value = html.escape(str(k["primer_gate"] or "—"))
    driver_value = html.escape(str(k["top_driver"] or "—"))
    validation_value = f'{k["validacion_arbol"]:.1f}%'

    st.markdown(
        f'<div class="flow-wrap">'
        f'<div class="flow-step">'
        f'<div class="flow-kicker">1 · Lo primero que se decide</div>'
        f'<div class="flow-value">{first_value}</div>'
        f'<div class="flow-note">Es el criterio que aparece primero al comenzar la elección.</div>'
        f'</div>'
        f'<div class="flow-arrow">→</div>'
        f'<div class="flow-step">'
        f'<div class="flow-kicker">2 · Lo que más pesa</div>'
        f'<div class="flow-value">{driver_value}</div>'
        f'<div class="flow-note">Es el factor con mayor importancia relativa al elegir entre alternativas.</div>'
        f'</div>'
        f'<div class="flow-arrow">→</div>'
        f'<div class="flow-step">'
        f'<div class="flow-kicker">3 · Qué tan bien representa la compra</div>'
        f'<div class="flow-value">{validation_value}</div>'
        f'<div class="flow-note">Porcentaje que confirma que la secuencia refleja su forma de decidir.</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("#### ¿Qué pasa si una opción no está disponible?")
    st.caption("Estas tres medidas muestran qué tan fácil es que el comprador cambie de opción o mantenga la compra.")

    substitution_view = pd.DataFrame({
        "situacion": [
            "Falta su marca → cambia de marca",
            "Falta su tono → cambia de marca",
            "No hay promoción → compra igual",
        ],
        "porcentaje": [
            k["cambia_marca_si_falta_marca"],
            k["cambia_marca_para_conservar_tono"],
            k["compra_sin_promocion"],
        ],
    })
    substitution_view["valor"] = substitution_view["porcentaje"].map(lambda x: f"{x:.1f}%")

    fig_sub = px.bar(
        substitution_view,
        x="porcentaje",
        y="situacion",
        orientation="h",
        text="valor",
        title="Respuesta ante ausencia de marca, tono o promoción",
        labels={"porcentaje": "Porcentaje", "situacion": ""},
    )
    fig_sub.update_traces(textposition="inside", insidetextanchor="end", textfont_size=14)
    fig_sub.update_layout(
        yaxis={"categoryorder":"array", "categoryarray":substitution_view["situacion"].tolist()[::-1]},
        xaxis_range=[0, 100],
        showlegend=False,
    )
    polish_bar(fig_sub, height=330, percent_axis=True)
    st.plotly_chart(fig_sub, use_container_width=True)

    if is_tendential:
        stage = decision_stage_tendential(filtered, reference).rename(columns={"tendencial": "porcentaje"})
    else:
        stage = decision_stage_summary(filtered).rename(columns={"pct": "porcentaje"})
    stage["valor"] = stage["porcentaje"].map(lambda x: f"{x:.1f}%")

    fig = px.bar(
        stage,
        x="porcentaje",
        y="criterio",
        color="etapa",
        barmode="group",
        orientation="h",
        text="valor",
        labels={"porcentaje": "Porcentaje", "criterio": "", "etapa": "Momento"},
        title="Qué se toma en cuenta en cada momento de la compra",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    polish_bar(fig, height=560, percent_axis=True)
    st.plotly_chart(fig, use_container_width=True)

    routes = top_routes(filtered, 8).rename(
        columns={"ruta": "Ruta de decisión", "n": "Entrevistas", "pct": "Porcentaje"}
    )
    st.markdown("#### Las rutas de decisión más frecuentes")
    st.caption("Muestran las combinaciones que realmente aparecieron en las entrevistas.")
    st.dataframe(
        routes.style.format({"Porcentaje": "{:.1f}%"}),
        use_container_width=True,
        hide_index=True,
    )

elif page == "Cómo se decide":
    st.markdown("### Cómo se decide la compra")
    st.caption("Lee el recorrido de izquierda a derecha: primero qué se decide, después qué se compara y al final qué termina definiendo la compra.")

    choices = ["Todos"] + options_for(filtered, "decision_1")
    sel = st.selectbox("Quiero ver el recorrido que empieza por:", choices, index=0)
    depth = st.slider(
        "Cuántas ramas mostrar",
        2,
        6,
        4,
        help="Menos ramas hacen el gráfico más simple; más ramas muestran mayor detalle.",
    )

    if is_tendential:
        links = tree_links_tendential(
            filtered,
            reference,
            None if sel == "Todos" else sel,
            top_d1=5,
            top_d2=depth,
            top_d3=max(2, depth - 1),
        )
    else:
        links = tree_links(filtered, None if sel == "Todos" else sel, top_d2=depth, top_d3=max(2, depth - 1))

    if not links["labels"]:
        st.warning("No hay información suficiente para mostrar este recorrido.")
    else:
        root_total = sum(v for src, v in zip(links["source"], links["value"]) if src == 0) or float(n)
        incoming = [0.0] * len(links["labels"])
        for tgt, val in zip(links["target"], links["value"]):
            incoming[tgt] += float(val)

        display_labels = []
        for idx, label in enumerate(links["labels"]):
            if idx == 0:
                display_labels.append(f"Compra<br>Base {n}")
            else:
                share = incoming[idx] / root_total * 100 if root_total else 0
                display_labels.append(f"{label}<br>{share:.1f}%")

        fig = go.Figure(
            go.Sankey(
                arrangement="snap",
                node=dict(label=display_labels, pad=22, thickness=20),
                link=dict(
                    source=links["source"],
                    target=links["target"],
                    value=links["value"],
                    customdata=links["custom"],
                    hovertemplate="%{source.label} → %{target.label}<br>%{customdata}<extra></extra>",
                ),
            )
        )
        fig.update_layout(
            title="Ruta de decisión de compra",
            height=720,
            font_size=13,
            margin=dict(l=10, r=10, t=65, b=15),
        )
        st.plotly_chart(fig, use_container_width=True)

        if is_tendential:
            st.caption("Los porcentajes visibles corresponden a la lectura tendencial. Al pasar el cursor sobre una rama verás el detalle de esa transición.")
        else:
            st.caption("Los porcentajes visibles muestran qué parte de la base sigue cada camino. Al pasar el cursor sobre una rama verás el detalle de esa transición.")

    st.markdown("#### Rutas observadas en la base")
    route_table = top_routes(filtered, 12).rename(
        columns={"ruta": "Ruta de decisión", "n": "Entrevistas", "pct": "Porcentaje"}
    )
    st.dataframe(
        route_table.style.format({"Porcentaje": "{:.1f}%"}),
        use_container_width=True,
        hide_index=True,
    )

elif page == "Qué pesa más":
    st.markdown("### Qué pesa más al elegir")
    st.caption("Entre más alto es el valor, mayor peso tiene ese factor en la elección del producto.")

    if is_tendential:
        comp = maxdiff_tendential(filtered, reference)
        plot = comp.melt(
            id_vars=["driver"],
            value_vars=["tendencial", "referencia"],
            var_name="serie",
            value_name="valor",
        )
        plot["serie"] = plot["serie"].map({"tendencial": "Producto · tendencial", "referencia": "Categoría"})
        plot["etiqueta"] = plot["valor"].map(lambda x: f"{x:.1f}")

        fig = px.bar(
            plot,
            x="valor",
            y="driver",
            color="serie",
            barmode="group",
            orientation="h",
            text="etiqueta",
            title="Factores que más influyen en la elección",
            labels={"valor": "Importancia", "driver": "", "serie": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        polish_bar(fig, height=600)
        st.plotly_chart(fig, use_container_width=True)

        table = comp[["driver", "observado", "tendencial", "referencia", "delta_vs_referencia"]].rename(
            columns={
                "driver": "Factor",
                "observado": "Dato observado",
                "tendencial": "Lectura tendencial",
                "referencia": "Categoría",
                "delta_vs_referencia": "Diferencia vs categoría",
            }
        )
        st.dataframe(
            table.style.format({
                "Dato observado": "{:.1f}",
                "Lectura tendencial": "{:.1f}",
                "Categoría": "{:.1f}",
                "Diferencia vs categoría": "{:+.1f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("La lectura tendencial conserva la señal del producto y la hace menos volátil cuando hay pocas entrevistas.")
    else:
        comp = maxdiff_compare(filtered, df)
        show_total = st.toggle("Comparar con el total", value=True)

        if show_total:
            plot = comp.melt(
                id_vars=["driver"],
                value_vars=["segmento", "total"],
                var_name="serie",
                value_name="valor",
            )
            plot["serie"] = plot["serie"].map({"segmento": "Selección actual", "total": "Total"})
        else:
            plot = comp[["driver", "segmento"]].rename(columns={"segmento": "valor"})
            plot["serie"] = "Selección actual"

        plot["etiqueta"] = plot["valor"].map(lambda x: f"{x:.1f}")
        fig = px.bar(
            plot,
            x="valor",
            y="driver",
            color="serie",
            barmode="group",
            orientation="h",
            text="etiqueta",
            title="Factores que más influyen en la elección",
            labels={"valor": "Importancia", "driver": "", "serie": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        polish_bar(fig, height=600)
        st.plotly_chart(fig, use_container_width=True)

        table = comp[["driver", "segmento", "total", "delta"]].rename(
            columns={
                "driver": "Factor",
                "segmento": "Selección actual",
                "total": "Total",
                "delta": "Diferencia",
            }
        )
        st.dataframe(
            table.style.format({"Selección actual": "{:.1f}", "Total": "{:.1f}", "Diferencia": "{:+.1f}"}),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("El valor sirve para comparar la importancia relativa de los factores: un número mayor significa que ese factor pesa más.")

elif page == "Qué pasa si falta...":
    st.markdown("### Qué pasa cuando algo no está disponible")
    st.caption("Explora qué harían los compradores si no encuentran la marca, el tono o la promoción que esperaban.")

    if is_tendential:
        k = tendential_kpis(filtered, reference)
    else:
        k = substitution_kpis(filtered)

    a, b, c = st.columns(3)
    a.metric("Si falta su marca, cambia de marca", f"{k['cambia_marca_si_falta_marca']:.1f}%")
    b.metric("Si falta su tono, cambia de marca", f"{k['cambia_marca_para_conservar_tono']:.1f}%")
    c.metric("Sin promoción, compra igual", f"{k['compra_sin_promocion']:.1f}%")

    scenario = st.selectbox(
        "Quiero probar qué pasa cuando:",
        ["Marca no disponible", "Tono/color no disponible", "Sin promoción"],
    )
    sim_n = st.slider("Número de compradores para visualizar", 100, 5000, 1000, 100)

    if is_tendential:
        t = substitution_tendential(filtered, reference, scenario).copy()
        t["esperados"] = (t["tendencial"] * sim_n / 100).round().astype(int)
        t["etiqueta"] = t.apply(lambda r: f"{r['tendencial']:.1f}% · {int(r['esperados'])}", axis=1)
        fig = px.bar(
            t,
            x="tendencial",
            y="respuesta",
            orientation="h",
            text="etiqueta",
            title="Qué harían los compradores",
            labels={"tendencial": "Porcentaje", "respuesta": ""},
        )
    else:
        t = scenario_counts(filtered, scenario, sim_n).copy()
        t["etiqueta"] = t.apply(lambda r: f"{r['pct']:.1f}% · {int(r['esperados'])}", axis=1)
        fig = px.bar(
            t,
            x="pct",
            y="respuesta",
            orientation="h",
            text="etiqueta",
            title="Qué harían los compradores",
            labels={"pct": "Porcentaje", "respuesta": ""},
        )

    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    polish_bar(fig, height=500, percent_axis=True)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Ejemplo: “42.0% · 420” significa que 42% seguiría esa opción, equivalente a 420 de cada 1,000 compradores en la visualización. No es un pronóstico de ventas.")

elif page == "Cómo ordenar el anaquel":
    st.markdown("### Cómo facilitar la compra en anaquel")
    st.caption("Muestra qué forma de organizar el anaquel ayuda más a encontrar rápidamente el producto.")

    if is_tendential:
        priority = shelf_priority_tendential(filtered, reference)
        priority["etiqueta"] = priority["indice_tendencial"].map(lambda x: f"{x:.1f}")
        fig = px.bar(
            priority,
            x="indice_tendencial",
            y="organizacion",
            orientation="h",
            text="etiqueta",
            title="Qué organización ayuda más",
            labels={"indice_tendencial": "Prioridad", "organizacion": ""},
        )
    else:
        priority = shelf_priority(filtered)
        priority["etiqueta"] = priority["indice_prioridad"].map(lambda x: f"{x:.1f}")
        fig = px.bar(
            priority,
            x="indice_prioridad",
            y="organizacion",
            orientation="h",
            text="etiqueta",
            title="Qué organización ayuda más",
            labels={"indice_prioridad": "Prioridad", "organizacion": ""},
        )

    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    polish_bar(fig, height=500)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("El valor combina lo que las personas mencionaron como primera y segunda ayuda. Más alto = mayor prioridad.")

    opts = priority["organizacion"].tolist()
    left, right = st.columns(2)
    primary = left.selectbox("Primero organizar por:", opts, index=0)
    sec_opts = [x for x in opts if x != primary]
    secondary = right.selectbox("Después organizar por:", sec_opts, index=0)

    if is_tendential:
        pair = shelf_pair_tendential(filtered, reference, primary, secondary)
        easy, barriers = friction_tendential(filtered, reference)
        easy_value = easy["tendencial"]
    else:
        pair = shelf_pair_score(filtered, primary, secondary)
        easy_value, barriers = friction_summary(filtered)

    x, y, z = st.columns(3)
    x.metric("Coincide exactamente con esta combinación", f"{pair['exact_order']:.1f}%")
    y.metric("Estas dos opciones aparecen entre las 2 principales", f"{pair['top2_any_order']:.1f}%")
    z.metric("Al menos una de las dos ayuda", f"{pair['coverage']:.1f}%")

    st.markdown(f"**{easy_value:.1f}%** encontró el producto fácil o muy fácil.")

    if len(barriers):
        if is_tendential:
            barriers = barriers.copy()
            barriers["etiqueta"] = barriers["tendencial"].map(lambda x: f"{x:.1f}%")
            fig2 = px.bar(
                barriers,
                x="tendencial",
                y="barrera",
                orientation="h",
                text="etiqueta",
                title="Qué dificulta encontrar el producto",
                labels={"tendencial": "Porcentaje", "barrera": ""},
            )
        else:
            barriers = barriers.copy()
            barriers["etiqueta"] = barriers["pct"].map(lambda x: f"{x:.1f}%")
            fig2 = px.bar(
                barriers,
                x="pct",
                y="barrera",
                orientation="h",
                text="etiqueta",
                title="Qué dificulta encontrar el producto",
                labels={"pct": "Porcentaje", "barrera": ""},
            )
        fig2.update_traces(textposition="outside")
        fig2.update_layout(yaxis={"categoryorder": "total ascending"})
        polish_bar(fig2, height=420, percent_axis=True)
        st.plotly_chart(fig2, use_container_width=True)

    st.caption("Esta lectura ayuda a comparar formas de organizar el anaquel. No estima un incremento directo de ventas.")


st.divider()
st.caption(
    f"{meta.get('project_name', 'Proyecto')} · Lectura {reading_mode.lower()} · "
    f"Base real: {n} entrevistas · Archivo procesado únicamente durante esta sesión."
)
