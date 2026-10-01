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
    categorical_tendential,
)

st.set_page_config(page_title="Wella | Decision Simulator", page_icon="🎯", layout="wide")

st.markdown(
    """
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
[data-testid="stToolbar"] {display:none !important;}
[data-testid="stDecoration"] {display:none !important;}
[data-testid="stStatusWidget"] {visibility:hidden;}
.block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1500px;}
[data-testid="stMetric"] {background: #F7F9FC; border: 1px solid #E3E8EF; padding: 12px; border-radius: 14px;}
.small-note {font-size: .82rem; color: #667085;}
.brand-shell {
    display:grid;
    grid-template-columns:170px minmax(0,1fr);
    border-radius:22px;
    overflow:hidden;
    margin-bottom:14px;
    border:1px solid #DCE5EE;
    background:#FFFFFF;
}
.brand-rail {
    background:linear-gradient(145deg,#0A2B4C,#173F6A);
    color:white;
    padding:22px 18px;
    display:flex;
    flex-direction:column;
    justify-content:space-between;
    min-height:138px;
}
.brand-wave {margin-bottom:8px;}
.brand-word {font-size:1.45rem;font-weight:800;letter-spacing:.06em;}
.brand-tag {font-size:.76rem;line-height:1.3;opacity:.86;margin-top:14px;}
.brand-main {
    padding:22px 28px 18px 28px;
    display:flex;
    flex-direction:column;
    justify-content:center;
    min-width:0;
}
.brand-kicker {
    font-size:.82rem;
    font-weight:800;
    color:#426180;
    text-transform:uppercase;
    letter-spacing:.04em;
}
.brand-title {
    font-size:2rem;
    line-height:1.08;
    color:#0E3155;
    font-weight:800;
    margin:4px 0 8px 0;
}
.brand-sub {
    color:#65758A;
    font-size:.98rem;
    line-height:1.4;
}
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
.exec-grid {
    display:grid;
    grid-template-columns:repeat(3, minmax(0, 1fr));
    gap:16px;
    margin:8px 0 20px 0;
}
.exec-card {
    border:1px solid #D7E3EF;
    border-radius:20px;
    background:linear-gradient(180deg,#FFFFFF 0%,#FBFDFF 100%);
    padding:18px 18px 16px 18px;
    min-height:300px;
    box-shadow:0 1px 0 rgba(18,52,86,.03);
}
.exec-head {
    display:flex;
    align-items:flex-start;
    gap:12px;
    margin-bottom:14px;
}
.exec-icon {
    width:54px;
    height:54px;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    flex:0 0 auto;
}
.exec-title {
    font-size:0.88rem;
    font-weight:800;
    color:#173A5E;
    text-transform:uppercase;
    letter-spacing:.02em;
    line-height:1.25;
}
.exec-subtitle {
    font-size:.82rem;
    color:#6B7C93;
    line-height:1.35;
    margin-top:4px;
}
.rank-row {
    display:grid;
    grid-template-columns:30px minmax(0,1fr) 132px;
    align-items:center;
    gap:10px;
    padding:10px 0;
    border-top:1px solid #EDF1F5;
}
.rank-side {display:flex;align-items:center;gap:8px;justify-content:flex-end;}
.mini-track {width:76px;height:10px;border-radius:999px;background:#EDF3F8;overflow:hidden;}
.mini-fill {height:100%;border-radius:999px;}
.rank-badge {
    width:28px;
    height:28px;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    font-weight:800;
    font-size:.82rem;
}
.rank-label {
    font-size:.94rem;
    color:#17324E;
    font-weight:600;
    line-height:1.25;
    min-width:0;
    overflow-wrap:anywhere;
}
.rank-value {
    font-size:1.02rem;
    color:#0C3762;
    font-weight:800;
    white-space:nowrap;
}
.section-card {
    border:1px solid #DCE5EE;
    border-radius:20px;
    background:#FFFFFF;
    padding:18px;
    height:100%;
}
.section-title {
    font-size:1.15rem;
    color:#153A60;
    font-weight:800;
    margin-bottom:4px;
}
.section-sub {
    font-size:.84rem;
    color:#728096;
    margin-bottom:10px;
    line-height:1.35;
}
.insight-callout {
    margin-top:12px;
    border-radius:14px;
    padding:12px 14px;
    background:#F5F9FD;
    color:#173A5E;
    font-size:.88rem;
    line-height:1.4;
    border:1px solid #E2EBF3;
}
.implications {
    margin-top:18px;
    border-radius:20px;
    background:linear-gradient(135deg,#0A2A4A,#153F6A);
    padding:18px;
    color:#FFFFFF;
}
.implications-title {
    font-size:1.12rem;
    font-weight:800;
    margin-bottom:12px;
}
.imp-grid {
    display:grid;
    grid-template-columns:repeat(3,minmax(0,1fr));
    gap:12px;
}
.imp-card {
    border-radius:16px;
    background:rgba(255,255,255,.96);
    color:#17324E;
    padding:15px;
    min-height:120px;
}
.imp-kicker {
    font-size:.8rem;
    font-weight:800;
    text-transform:uppercase;
    letter-spacing:.03em;
    margin-bottom:6px;
}
.imp-main {
    font-size:1rem;
    font-weight:800;
    line-height:1.3;
}
.imp-note {
    font-size:.82rem;
    color:#64748B;
    line-height:1.35;
    margin-top:6px;
}
.summary-grid {
    display:grid;
    grid-template-columns:1.45fr 1fr .95fr;
    gap:16px;
    align-items:stretch;
    margin-top:16px;
}
.summary-panel {
    border:1px solid #DCE5EE;
    border-radius:20px;
    background:#FFFFFF;
    padding:17px 18px;
    min-width:0;
    height:100%;
    display:flex;
    flex-direction:column;
}
.summary-panel > .insight-callout {
    margin-top:auto !important;
}
.panel-head {
    font-size:1.05rem;
    font-weight:800;
    color:#153A60;
    margin-bottom:2px;
}
.panel-sub {
    font-size:.8rem;
    color:#718096;
    line-height:1.35;
    margin-bottom:12px;
}
.reach-legend {display:flex;gap:13px;flex-wrap:wrap;font-size:.75rem;color:#607085;margin-bottom:10px;}
.legend-dot {width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:5px;}
.reach-row {
    display:grid;
    grid-template-columns:135px minmax(0,1fr) 58px 54px;
    gap:8px;
    align-items:center;
    margin:9px 0;
}
.reach-label {font-size:.82rem;color:#1F3B58;line-height:1.15;overflow-wrap:anywhere;}
.reach-track {height:20px;background:#EEF3F7;border-radius:5px;overflow:hidden;display:flex;}
.seg-first {background:#175EA8;}
.seg-second {background:#4D92E8;}
.seg-close {background:#A9CDF4;}
.seg-label {font-size:.68rem;color:white;display:flex;align-items:center;justify-content:center;white-space:nowrap;overflow:hidden;}
.seg-close .seg-label {color:#173A5E;}
.reach-total {font-weight:800;color:#153A60;font-size:.84rem;text-align:right;}
.reach-1000 {font-size:.74rem;color:#74859A;text-align:right;}
.driver-row {
    display:grid;
    grid-template-columns:minmax(0,1fr) 110px 42px;
    gap:8px;
    align-items:center;
    margin:10px 0;
}
.driver-label {font-size:.8rem;color:#1D3A57;line-height:1.15;}
.driver-track {height:19px;background:#EEF3F7;border-radius:5px;overflow:hidden;}
.driver-fill {height:100%;border-radius:5px;background:linear-gradient(90deg,#0E5BA8,#2E8CE3);}
.driver-value {font-weight:800;color:#173A5E;font-size:.86rem;}
.sub-row {
    display:grid;
    grid-template-columns:48px 66px minmax(0,1fr);
    gap:10px;
    align-items:center;
    padding:10px 0;
    border-top:1px solid #EEF2F6;
}
.sub-icon {width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;}
.sub-value {font-size:1.25rem;font-weight:800;color:#13395F;}
.sub-label {font-size:.79rem;color:#304A63;line-height:1.25;}

.nav-kicker {
    text-align:center;
    font-size:.78rem;
    font-weight:800;
    letter-spacing:.28em;
    color:#6E87A5;
    margin-top:8px;
    margin-bottom:6px;
}
.nav-kicker::before,.nav-kicker::after {
    content:"";
    display:inline-block;
    width:42px;
    height:1px;
    background:#AFC2D6;
    vertical-align:middle;
    margin:0 14px;
}
.nav-title {
    text-align:center;
    color:#092D56;
    font-size:2rem;
    font-weight:800;
    line-height:1.08;
    margin-bottom:5px;
}
.nav-subtitle {
    text-align:center;
    color:#6E8096;
    font-size:.94rem;
    margin-bottom:16px;
}
.st-key-study_nav [data-testid="stButton"] > button {
    width:100%;
    min-height:142px;
    border-radius:20px !important;
    border:1px solid #D8E3EE;
    box-shadow:0 6px 18px rgba(27,64,102,.04);
    font-size:1rem;
    font-weight:750;
    color:#163858;
    background:linear-gradient(180deg,#FFFFFF 0%,#FBFDFF 100%);
    transition:all .16s ease;
    padding:14px 10px !important;
    display:flex;
    flex-direction:column;
    justify-content:center;
    gap:9px;
}
.st-key-study_nav [data-testid="stButton"] > button:hover {
    border-color:#73A7D8;
    box-shadow:0 7px 22px rgba(27,85,140,.10);
    transform:translateY(-1px);
}
.st-key-study_nav [data-testid="stButton"] > button[kind="primary"] {
    border:2px solid #1776C8 !important;
    background:linear-gradient(180deg,#F7FBFF 0%,#EDF6FF 100%) !important;
    color:#0E4C82 !important;
    box-shadow:0 8px 22px rgba(22,118,200,.13);
}
.st-key-study_nav [data-testid="stIconMaterial"] {
    font-size:2.45rem !important;
    line-height:1 !important;
    margin:0 !important;
    color:#1766AA;
}
.st-key-study_nav button[kind="primary"] [data-testid="stIconMaterial"] {
    color:#0B67B4 !important;
}
.st-key-study_nav [data-testid="stButton"] p {
    font-size:1rem !important;
    line-height:1.18 !important;
    font-weight:750 !important;
    text-align:center !important;
}
.nav-status {
    text-align:center;
    margin-top:7px;
    font-size:.73rem;
    font-weight:800;
    letter-spacing:.05em;
    color:#8294AA;
    min-height:18px;
}
.nav-status.active {
    color:#0C68B5;
}
.nav-connector {
    height:142px;
    display:flex;
    align-items:center;
    justify-content:center;
}
.nav-connector-line {
    width:100%;
    height:2px;
    background:#B7C8DA;
    position:relative;
}
.nav-connector-line::after {
    content:"";
    width:10px;
    height:10px;
    border-radius:50%;
    background:#FFFFFF;
    border:2px solid #8FA8C0;
    position:absolute;
    left:50%;
    top:50%;
    transform:translate(-50%,-50%);
}
.nav-guide {
    margin:14px 0 20px 0;
    border-radius:16px;
    background:linear-gradient(90deg,#F3F7FB,#FAFCFE);
    border:1px solid #E7EDF3;
    padding:13px 18px;
    display:flex;
    gap:13px;
    align-items:center;
    justify-content:center;
    color:#71859D;
    font-size:.84rem;
    line-height:1.35;
}
.nav-guide-icon {
    width:30px;
    height:30px;
    border:2px solid #8CA3BA;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    flex:0 0 auto;
}

@media (max-width: 1050px) {
    .summary-grid {grid-template-columns:1fr;}
    .brand-shell {grid-template-columns:130px minmax(0,1fr);}
}
@media (max-width: 900px) {
    .st-key-study_nav [data-testid="stHorizontalBlock"] {gap:.45rem !important;}
    .st-key-study_nav [data-testid="stButton"] > button {min-height:100px;font-size:.84rem;}
    .st-key-study_nav [data-testid="stIconMaterial"] {font-size:1.9rem !important;}
    .nav-connector {display:none;}
    .exec-grid {grid-template-columns:1fr;}
    .imp-grid {grid-template-columns:1fr;}
    .flow-wrap {grid-template-columns:1fr; gap:8px;}
    .flow-arrow {transform:rotate(90deg); min-height:24px;}
    .brand-shell {grid-template-columns:1fr;}
    .brand-rail {min-height:auto;}
    .reach-row {grid-template-columns:110px minmax(0,1fr) 50px;}
    .reach-1000 {display:none;}
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '''
    <div class="brand-shell">
      <div class="brand-rail">
        <div>
          <div class="brand-wave">
            <svg width="82" height="34" viewBox="0 0 82 34" aria-hidden="true">
              <path d="M3 20 C18 5, 31 5, 46 18 S70 30,79 14" fill="none" stroke="white" stroke-width="2.4" stroke-linecap="round"/>
              <path d="M5 25 C20 10, 33 10, 48 22 S70 31,78 19" fill="none" stroke="white" stroke-width="2.1" stroke-linecap="round" opacity=".9"/>
              <path d="M8 29 C21 17, 34 16, 49 26 S69 32,76 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" opacity=".75"/>
            </svg>
          </div>
          <div class="brand-word">WELLA</div>
        </div>
        <div class="brand-tag">DECISIÓN DE COMPRA<br>COLORACIÓN</div>
      </div>
      <div class="brand-main">
        <div class="brand-kicker">Resumen ejecutivo</div>
        <div class="brand-title">Así deciden la compra de tintes para cabello</div>
        <div class="brand-sub">Una visión clara de qué consideran, qué genera valor y qué puede cambiar su elección.</div>
      </div>
    </div>
    ''',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="secure"><b>Acceso al estudio:</b> los resultados se muestran únicamente después de cargar el archivo correspondiente y su clave de acceso.</div>',
    unsafe_allow_html=True,
)


def clear_loaded_data() -> None:
    for key in ["dataset", "metadata", "package_fp", "loaded_name", "unlock_password", "insight_cache"]:
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


def icon_svg(kind: str, stroke: str = "#1D5E9E") -> str:
    """Inline SVG icons so the dashboard needs no external image files."""
    paths = {
        "hair": '<path d="M12 3.5c-4.7 0-7.7 3.2-7.7 8.2v7.1M12 3.5c4.7 0 7.7 3.2 7.7 8.2v7.1M7.2 18.8v-6.1c0-3.8 1.7-6.1 4.8-7.2M16.8 18.8v-6.1c0-3.8-1.7-6.1-4.8-7.2M9.3 10.4c.7-1.6 1.6-2.6 2.7-3.2 1.1.6 2 1.6 2.7 3.2M9.3 10.4v5.2c0 2.2 1.1 4 2.7 4.9 1.6-.9 2.7-2.7 2.7-4.9v-5.2" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round"/>',
        "diamond": '<path d="M5 9l3-4h8l3 4-7 10L5 9zM8 5l4 14 4-14M5 9h14" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>',
        "check": '<path d="M6 12l4 4 8-9" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>',
        "swap": '<path d="M5 8h11l-3-3m3 3-3 3M19 16H8l3 3m-3-3 3-3" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
        "tag": '<path d="M4 11V5h6l9 9-5 5-10-8zM8 8h.01" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"/>',
        "shield": '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6l7-3zM9 12l2 2 4-4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
        "megaphone": '<path d="M4 13h4l8 4V7l-8 4H4v2zM8 13l1 5h3" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
        "chart": '<path d="M5 18V9h3v9H5zm6 0V5h3v13h-3zm6 0v-6h3v6h-3z" fill="none" stroke="currentColor" stroke-width="1.6"/>',
        "warning": '<path d="M12 4l8 15H4L12 4zM12 9v4M12 16h.01" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    }
    body = paths.get(kind, paths["chart"])
    return (
        f'<svg width="28" height="28" viewBox="0 0 24 24" '
        f'style="color:{stroke};display:block" aria-hidden="true">{body}</svg>'
    )


def executive_stage_card(
    step: int,
    title: str,
    subtitle: str,
    rows: list[tuple[str, float]],
    icon: str,
    accent: str,
    bg: str,
) -> str:
    rank_html = ""
    max_value = max([float(v) for _, v in rows[:3]], default=1.0)
    for idx, (label, value) in enumerate(rows[:3], start=1):
        width = max(10.0, min(100.0, float(value) / max_value * 100.0))
        rank_html += (
            '<div class="rank-row">'
            f'<div class="rank-badge" style="background:{bg};color:{accent}">{idx}</div>'
            f'<div class="rank-label">{html.escape(str(label))}</div>'
            f'<div class="rank-side">'
            f'<div class="mini-track"><div class="mini-fill" style="width:{width:.1f}%;background:{accent}"></div></div>'
            f'<div class="rank-value">{value:.1f}%</div>'
            f'</div>'
            '</div>'
        )
    return (
        '<div class="exec-card">'
        '<div class="exec-head">'
        f'<div class="exec-icon" style="background:{bg};color:{accent}">{icon_svg(icon, accent)}</div>'
        '<div>'
        f'<div class="exec-title">{step} · {html.escape(title)}</div>'
        f'<div class="exec-subtitle">{html.escape(subtitle)}</div>'
        '</div></div>'
        f'{rank_html}'
        '</div>'
    )


def two_step_routes(data: pd.DataFrame, top_n: int = 8) -> pd.DataFrame:
    """Rutas de dos pasos con porcentaje condicional sobre el primer paso."""
    d = data[["decision_1", "decision_2"]].dropna()
    if d.empty:
        return pd.DataFrame(columns=["ruta", "entrevistas", "base_inicio", "porcentaje_dentro_inicio"])
    base = d["decision_1"].value_counts().rename("base_inicio")
    out = (
        d.groupby(["decision_1", "decision_2"])
        .size()
        .reset_index(name="entrevistas")
        .merge(base, left_on="decision_1", right_index=True, how="left")
    )
    out["porcentaje_dentro_inicio"] = out["entrevistas"] / out["base_inicio"] * 100
    out["ruta"] = out["decision_1"].astype(str) + " → " + out["decision_2"].astype(str)
    return (
        out.sort_values(["entrevistas", "porcentaje_dentro_inicio"], ascending=[False, False])
        [["ruta", "entrevistas", "base_inicio", "porcentaje_dentro_inicio"]]
        .head(top_n)
        .reset_index(drop=True)
    )


def decision_reach(stage: pd.DataFrame) -> pd.DataFrame:
    """Suma el peso de un criterio en D1, D2 y D3.

    La suma es válida porque el cuestionario no permite repetir el mismo criterio
    dentro de la secuencia D1 → D2 → D3.
    """
    needed = ["Primero", "Después", "Cierre"]
    p = (
        stage.pivot_table(index="criterio", columns="etapa", values="porcentaje", aggfunc="sum", fill_value=0)
        .reindex(columns=needed, fill_value=0)
        .reset_index()
    )
    p["Alcance"] = p[needed].sum(axis=1).clip(upper=100)
    p["Por cada 1,000"] = (p["Alcance"] * 10).round().astype(int)
    return p.sort_values("Alcance", ascending=False).reset_index(drop=True)


def conditional_reading(
    target_subset: pd.DataFrame,
    reference_subset: pd.DataFrame,
    broader_reference: pd.DataFrame,
    col: str,
    *,
    force_tendential: bool = False,
    strength: float = 16.0,
) -> tuple[pd.DataFrame, str, int]:
    """Distribución condicional simple; usa apoyo tendencial cuando la rama es pequeña."""
    base_n = int(target_subset[col].notna().sum()) if col in target_subset.columns else 0
    use_tendential = force_tendential or base_n < 30

    if use_tendential:
        ref = reference_subset if len(reference_subset) >= 20 else broader_reference
        t = categorical_tendential(
            target_subset,
            ref,
            col,
            strength=strength,
            label_name="opcion",
        )
        out = t[["opcion", "tendencial"]].rename(columns={"tendencial": "porcentaje"})
        mode = "Tendencial"
    else:
        counts = target_subset[col].dropna().value_counts()
        total = int(counts.sum())
        out = pd.DataFrame({
            "opcion": counts.index.astype(str),
            "porcentaje": counts.values / total * 100 if total else [],
        })
        mode = "Observada"

    out = out.sort_values("porcentaje", ascending=False).reset_index(drop=True)
    return out, mode, base_n


def conditional_bar(table: pd.DataFrame, title: str, top_n: int = 8):
    shown = table.head(top_n).copy()
    shown["valor"] = shown["porcentaje"].map(lambda x: f"{x:.1f}%")
    fig = px.bar(
        shown.sort_values("porcentaje"),
        x="porcentaje",
        y="opcion",
        orientation="h",
        text="valor",
        title=title,
        labels={"porcentaje": "Probabilidad dentro de esta etapa", "opcion": ""},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_range=[0, max(100, float(shown["porcentaje"].max()) * 1.18) if len(shown) else 100])
    polish_bar(fig, height=max(330, 70 + 42 * len(shown)), percent_axis=True)
    return fig


def _wrap_tree_label(text: str, width: int = 23) -> str:
    words = str(text).split()
    lines, current = [], []
    count = 0
    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and count + extra > width:
            lines.append(" ".join(current))
            current = [word]
            count = len(word)
        else:
            current.append(word)
            count += extra
    if current:
        lines.append(" ".join(current))
    return "<br>".join(lines)


def decision_tree_figure(
    data: pd.DataFrame,
    reference_data: pd.DataFrame,
    *,
    first_choice: str | None = None,
    force_tendential: bool = False,
    top_d1: int = 3,
    top_d2: int = 3,
    top_d3: int = 2,
) -> go.Figure:
    """Árbol visual con probabilidades condicionales por rama, sin multiplicarlas."""

    step1, mode1, base1 = conditional_reading(
        data,
        reference_data,
        reference_data,
        "decision_1",
        force_tendential=force_tendential,
        strength=12.0,
    )

    if first_choice and first_choice != "Todos":
        step1 = step1[step1["opcion"] == first_choice].copy()
    else:
        step1 = step1.head(top_d1).copy()

    branches = []
    for _, r1 in step1.iterrows():
        d1 = str(r1["opcion"])
        target1 = data[data["decision_1"] == d1].copy()
        ref1 = reference_data[reference_data["decision_1"] == d1].copy()

        step2, mode2, base2 = conditional_reading(
            target1,
            ref1,
            reference_data,
            "decision_2",
            force_tendential=force_tendential,
            strength=14.0,
        )
        step2 = step2[step2["opcion"] != d1].head(top_d2).copy()

        children2 = []
        for _, r2 in step2.iterrows():
            d2 = str(r2["opcion"])
            target12 = target1[target1["decision_2"] == d2].copy()
            ref12 = ref1[ref1["decision_2"] == d2].copy()
            broader_ref = ref1 if len(ref1) else reference_data

            step3, mode3, base3 = conditional_reading(
                target12,
                ref12,
                broader_ref,
                "decision_3",
                force_tendential=force_tendential,
                strength=12.0,
            )
            step3 = step3[~step3["opcion"].isin([d1, d2])].head(top_d3).copy()

            children3 = [
                {
                    "label": str(r3["opcion"]),
                    "pct": float(r3["porcentaje"]),
                    "base": base3,
                    "mode": mode3,
                }
                for _, r3 in step3.iterrows()
            ]
            children2.append({
                "label": d2,
                "pct": float(r2["porcentaje"]),
                "base": base2,
                "mode": mode2,
                "children": children3,
            })

        branches.append({
            "label": d1,
            "pct": float(r1["porcentaje"]),
            "base": base1,
            "mode": mode1,
            "children": children2,
        })

    # Assign vertical positions from leaves upward so branches do not overlap.
    cursor = 0.0
    for d1 in branches:
        d2_positions = []
        for d2 in d1["children"]:
            d3_positions = []
            if d2["children"]:
                for d3 in d2["children"]:
                    d3["y_raw"] = cursor
                    d3_positions.append(cursor)
                    cursor += 1.0
                d2["y_raw"] = sum(d3_positions) / len(d3_positions)
            else:
                d2["y_raw"] = cursor
                cursor += 1.0
            d2_positions.append(d2["y_raw"])
        if d2_positions:
            d1["y_raw"] = sum(d2_positions) / len(d2_positions)
        else:
            d1["y_raw"] = cursor
            cursor += 1.0

    max_y = max(cursor - 1.0, 1.0)

    def ny(v):
        return 1.0 - (v / max_y if max_y else 0.5)

    for d1 in branches:
        d1["y"] = ny(d1["y_raw"])
        for d2 in d1["children"]:
            d2["y"] = ny(d2["y_raw"])
            for d3 in d2["children"]:
                d3["y"] = ny(d3["y_raw"])

    root_y = sum(d["y"] for d in branches) / len(branches) if branches else 0.5
    fig = go.Figure()

    def add_edge(x0, y0, x1, y1, pct, base, mode):
        width = 1.8 + min(6.0, max(0.0, pct) / 12.0)
        fig.add_trace(go.Scatter(
            x=[x0, x1],
            y=[y0, y1],
            mode="lines",
            line=dict(width=width, color="rgba(70,105,140,0.38)"),
            hovertemplate=(
                f"<b>{pct:.1f}%</b> dentro de esta rama"
                f"<br>Base de la rama: {base}<extra></extra>"
            ),
            showlegend=False,
        ))
        fig.add_annotation(
            x=(x0 + x1) / 2,
            y=(y0 + y1) / 2,
            text=f"<b>{pct:.1f}%</b>",
            showarrow=False,
            bgcolor="rgba(255,255,255,0.88)",
            bordercolor="rgba(160,175,190,0.65)",
            borderwidth=1,
            borderpad=3,
            font=dict(size=11, color="#23415F"),
        )

    # Root node.
    fig.add_trace(go.Scatter(
        x=[0],
        y=[root_y],
        mode="markers+text",
        marker=dict(size=30, color="#0B3558"),
        text=["Compra"],
        textposition="middle right",
        textfont=dict(size=14, color="#102A43"),
        hovertemplate=f"Base actual: {len(data)} entrevistas<extra></extra>",
        showlegend=False,
    ))

    node_x, node_y, node_text, node_hover, node_size = [], [], [], [], []

    for d1 in branches:
        add_edge(0.05, root_y, 1.0, d1["y"], d1["pct"], d1["base"], d1["mode"])
        node_x.append(1.0); node_y.append(d1["y"])
        node_text.append(f"<b>{_wrap_tree_label(d1['label'])}</b><br>{d1['pct']:.1f}%")
        node_hover.append(f"Primero<br>{d1['pct']:.1f}%<br>Base de la rama: {d1['base']}")
        node_size.append(26)

        for d2 in d1["children"]:
            add_edge(1.05, d1["y"], 2.0, d2["y"], d2["pct"], d2["base"], d2["mode"])
            node_x.append(2.0); node_y.append(d2["y"])
            node_text.append(f"<b>{_wrap_tree_label(d2['label'])}</b><br>{d2['pct']:.1f}%")
            node_hover.append(
                f"Después de {d1['label']}<br>{d2['pct']:.1f}%<br>"
                f"Base de la rama: {d2['base']}"
            )
            node_size.append(22)

            for d3 in d2["children"]:
                add_edge(2.05, d2["y"], 3.0, d3["y"], d3["pct"], d3["base"], d3["mode"])
                node_x.append(3.0); node_y.append(d3["y"])
                node_text.append(f"<b>{_wrap_tree_label(d3['label'])}</b><br>{d3['pct']:.1f}%")
                node_hover.append(
                    f"Cierre después de {d1['label']} → {d2['label']}<br>{d3['pct']:.1f}%<br>"
                    f"Base de la rama: {d3['base']}"
                )
                node_size.append(19)

    if node_x:
        fig.add_trace(go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            marker=dict(
                size=node_size,
                color=["#2F6B8F" if x == 1.0 else "#6A91AB" if x == 2.0 else "#A5BBCB" for x in node_x],
                line=dict(width=1, color="white"),
            ),
            text=node_text,
            customdata=node_hover,
            hovertemplate="%{customdata}<extra></extra>",
            textposition="middle right",
            textfont=dict(size=11, color="#102A43"),
            showlegend=False,
        ))

    fig.add_annotation(x=0, y=1.08, text="<b>Inicio</b>", showarrow=False, font=dict(size=13))
    fig.add_annotation(x=1, y=1.08, text="<b>Primero</b>", showarrow=False, font=dict(size=13))
    fig.add_annotation(x=2, y=1.08, text="<b>Después</b>", showarrow=False, font=dict(size=13))
    fig.add_annotation(x=3, y=1.08, text="<b>Cierre</b>", showarrow=False, font=dict(size=13))

    fig.update_layout(
        title="Árbol de decisión · probabilidades dentro de cada rama",
        height=max(650, 110 + int(cursor) * 42),
        margin=dict(l=25, r=240, t=80, b=35),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(range=[-0.1, 3.55], visible=False, fixedrange=True),
        yaxis=dict(range=[-0.08, 1.13], visible=False, fixedrange=True),
        hovermode="closest",
    )
    return fig


INSIGHT_ENGINE_VERSION = "1.0"


def _filter_signature(filters: dict, reading_mode: str, n: int) -> tuple:
    """Stable key: same dataset/filter state -> same insight text."""
    normalized = []
    for key in sorted(filters):
        value = filters.get(key)
        if isinstance(value, list):
            normalized.append((key, tuple(sorted(str(v) for v in value))))
        elif value is None:
            normalized.append((key, ()))
        else:
            normalized.append((key, (str(value),)))
    return (INSIGHT_ENGINE_VERSION, tuple(normalized), str(reading_mode), int(n))


def build_dynamic_insights(
    alcance: pd.DataFrame,
    md: pd.DataFrame,
    k: dict,
) -> dict:
    """Generate client-facing insights using deterministic rules only."""
    insights = {
        "reach": "La lectura cambia automáticamente con la selección actual.",
        "drivers": "Los factores con mayor peso cambian con la selección actual.",
        "substitution": "La respuesta ante faltantes cambia con la selección actual.",
    }

    # 1) Reach insight
    if alcance is not None and len(alcance):
        r = alcance.sort_values("Alcance", ascending=False).reset_index(drop=True)
        top = r.iloc[0]
        second = r.iloc[1] if len(r) > 1 else top
        gap = float(top["Alcance"]) - float(second["Alcance"])
        moment_cols = ["Primero", "Después", "Cierre"]
        dominant_moment = max(moment_cols, key=lambda c: float(top.get(c, 0.0)))
        dominant_value = float(top.get(dominant_moment, 0.0))
        top_name = str(top["criterio"])
        top_reach = float(top["Alcance"])

        if gap >= 10:
            lead_phrase = f"lidera con claridad y supera al segundo criterio por {gap:.1f} puntos"
        elif gap >= 3:
            lead_phrase = f"mantiene el mayor alcance, {gap:.1f} puntos por encima del segundo criterio"
        else:
            lead_phrase = "comparte un nivel de alcance muy cercano con el siguiente criterio"

        insights["reach"] = (
            f"<b>{html.escape(top_name)}</b> alcanza a <b>{top_reach:.1f}%</b> de los compradores; "
            f"{lead_phrase}. Su mayor presencia ocurre en <b>{dominant_moment.lower()}</b> "
            f"({dominant_value:.1f}%)."
        )

    # 2) Driver insight
    if md is not None and len(md):
        d = md.sort_values("valor", ascending=False).reset_index(drop=True)
        top = d.iloc[0]
        second = d.iloc[1] if len(d) > 1 else top
        top_name = str(top["driver"])
        second_name = str(second["driver"])
        top_value = float(top["valor"])
        second_value = float(second["valor"])
        gap = top_value - second_value

        if gap >= 2.0:
            relation = f"muestra una ventaja clara de {gap:.1f} puntos"
        elif gap >= 0.7:
            relation = f"mantiene una ventaja moderada de {gap:.1f} puntos"
        else:
            relation = "comparte prácticamente el liderazgo"

        insights["drivers"] = (
            f"<b>{html.escape(top_name)}</b> es el factor con mayor peso ({top_value:.1f}); "
            f"{relation} frente a <b>{html.escape(second_name)}</b> ({second_value:.1f})."
        )

    # 3) Substitution insight
    brand = float(k.get("cambia_marca_si_falta_marca", 0.0))
    tone = float(k.get("cambia_marca_para_conservar_tono", 0.0))
    promo = float(k.get("compra_sin_promocion", 0.0))

    if brand >= 65:
        brand_phrase = f"la falta de marca genera un riesgo alto de sustitución ({brand:.1f}%)"
    elif brand >= 45:
        brand_phrase = f"la falta de marca genera un riesgo relevante de sustitución ({brand:.1f}%)"
    else:
        brand_phrase = f"la falta de marca muestra un riesgo contenido de sustitución ({brand:.1f}%)"

    if tone >= 50:
        tone_phrase = f"el tono también domina con fuerza sobre la lealtad a marca ({tone:.1f}%)"
    elif tone >= 30:
        tone_phrase = f"el tono también puede provocar cambio de marca ({tone:.1f}%)"
    else:
        tone_phrase = f"el tono provoca menor cambio de marca ({tone:.1f}%)"

    if promo >= 60:
        promo_phrase = f"mientras que la promoción es menos determinante: {promo:.1f}% compraría aun sin ella"
    elif promo >= 40:
        promo_phrase = f"y la ausencia de promoción divide más la decisión: {promo:.1f}% compraría aun sin ella"
    else:
        promo_phrase = f"y la promoción tiene mayor capacidad de retener la compra: sólo {promo:.1f}% compraría sin ella"

    insights["substitution"] = (
        f"{brand_phrase}; {tone_phrase}; {promo_phrase}."
    )

    return insights


def get_cached_dynamic_insights(
    filters: dict,
    reading_mode: str,
    n: int,
    alcance: pd.DataFrame,
    md: pd.DataFrame,
    k: dict,
) -> dict:
    """Cache by a stable filter key; deterministic across repeated selections."""
    key = _filter_signature(filters, reading_mode, n)
    cache = st.session_state.setdefault("insight_cache", {})
    if key not in cache:
        cache[key] = build_dynamic_insights(alcance, md, k)
    return cache[key]


def reach_panel_html(alcance: pd.DataFrame, insight: str) -> str:
    """Render alcance with the largest criterion normalized to 100 visual points."""
    rows = ""
    display = alcance.head(6).copy()
    max_total = max(float(display["Alcance"].max()), 1.0)

    for _, row in display.iterrows():
        first = float(row.get("Primero", 0.0))
        second = float(row.get("Después", 0.0))
        close = float(row.get("Cierre", 0.0))
        total = float(row.get("Alcance", 0.0))

        # Normalize the visual bar to the highest-reach criterion.
        # The labels still show the true observed/tendential percentages.
        first_w = first / max_total * 100.0
        second_w = second / max_total * 100.0
        close_w = close / max_total * 100.0
        relative_index = total / max_total * 100.0

        def seg_label(value: float, normalized_width: float) -> str:
            return f"{value:.1f}%" if normalized_width >= 11 else ""

        rows += (
            '<div class="reach-row">'
            f'<div class="reach-label">{html.escape(str(row["criterio"]))}</div>'
            '<div class="reach-track">'
            f'<div class="seg-first" style="width:{first_w:.2f}%"><span class="seg-label">{seg_label(first, first_w)}</span></div>'
            f'<div class="seg-second" style="width:{second_w:.2f}%"><span class="seg-label">{seg_label(second, second_w)}</span></div>'
            f'<div class="seg-close" style="width:{close_w:.2f}%"><span class="seg-label">{seg_label(close, close_w)}</span></div>'
            '</div>'
            f'<div class="reach-total">{total:.1f}%</div>'
            f'<div class="reach-1000">{int(row["Por cada 1,000"])}</div>'
            '</div>'
        )

    return (
        '<div class="summary-panel">'
        '<div class="panel-head">Qué elementos intervienen en la decisión</div>'
        '<div class="panel-sub">El criterio con mayor alcance se muestra como 100 visual. Las cifras dentro de las barras conservan el porcentaje real.</div>'
        '<div class="reach-legend">'
        '<span><span class="legend-dot" style="background:#175EA8"></span>Primero</span>'
        '<span><span class="legend-dot" style="background:#4D92E8"></span>Después</span>'
        '<span><span class="legend-dot" style="background:#A9CDF4"></span>Cierre</span>'
        '<span style="margin-left:auto"><b>Alcance real</b> · de 1,000</span>'
        '</div>'
        f'{rows}'
        '<div class="insight-callout" style="margin-top:14px">'
        f'{icon_svg("chart", "#1D5E9E")} {insight}'
        '</div>'
        '</div>'
    )


def drivers_panel_html(md: pd.DataFrame, insight: str) -> str:
    ordered = md.sort_values("valor", ascending=False).head(5).copy()
    max_value = max(float(ordered["valor"].max()), 1.0)
    rows = ""
    accents = ["#0F5DA9", "#2D86DD", "#21A6A0", "#4DBD78", "#8DC95C"]
    for idx, (_, row) in enumerate(ordered.iterrows()):
        value = float(row["valor"])
        width = max(8.0, min(100.0, value / max_value * 100.0))
        color = accents[min(idx, len(accents)-1)]
        rows += (
            '<div class="driver-row">'
            f'<div class="driver-label">{html.escape(str(row["driver"]))}</div>'
            f'<div class="driver-track"><div class="driver-fill" style="width:{width:.1f}%;background:{color}"></div></div>'
            f'<div class="driver-value">{value:.1f}</div>'
            '</div>'
        )
    return (
        '<div class="summary-panel">'
        '<div class="panel-head">Qué genera mayor valor al elegir</div>'
        '<div class="panel-sub">Factores con mayor importancia relativa.</div>'
        f'{rows}'
        '<div class="insight-callout">'
        f'{icon_svg("diamond", "#5B4AE6")} {insight}'
        '</div>'
        '</div>'
    )


def substitution_panel_html(k: dict, insight: str) -> str:
    rows = [
        ("swap", "#D84B65", "#FDECEF", float(k["cambia_marca_si_falta_marca"]), "Cambia de marca si no encuentra su marca"),
        ("hair", "#E7862E", "#FFF2E6", float(k["cambia_marca_para_conservar_tono"]), "Cambia de marca para conservar su tono"),
        ("tag", "#6754D9", "#F0EDFF", float(k["compra_sin_promocion"]), "Compra aun sin promoción"),
    ]
    html_rows = ""
    for icon, accent, bg, value, label in rows:
        html_rows += (
            '<div class="sub-row">'
            f'<div class="sub-icon" style="background:{bg};color:{accent}">{icon_svg(icon, accent)}</div>'
            f'<div class="sub-value">{value:.1f}%</div>'
            f'<div class="sub-label">{html.escape(label)}</div>'
            '</div>'
        )
    return (
        '<div class="summary-panel">'
        '<div class="panel-head">Qué pasa si no encuentro lo que quiero</div>'
        '<div class="panel-sub">Situaciones que pueden cambiar la elección.</div>'
        f'{html_rows}'
        '<div class="insight-callout" style="background:#FFF3F4;border-color:#F6DDE0;color:#8E3243">'
        f'{icon_svg("warning", "#C7435B")} {insight}'
        '</div>'
        '</div>'
    )


uploaded = st.file_uploader(
    "1. Carga el archivo del estudio",
    type=["goideas"],
    help="Selecciona el archivo asignado a este estudio.",
)

if uploaded is None:
    if "dataset" in st.session_state:
        clear_loaded_data()
    st.info("Para comenzar, carga el archivo del estudio y después introduce tu clave de acceso.")
    st.caption("Los resultados estarán disponibles después de validar el acceso.")
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
    password = st.text_input("2. Clave de acceso", type="password", key="unlock_password")
    unlock = st.button("Abrir estudio", type="primary", use_container_width=True)

    if not unlock:
        st.caption("Introduce tu clave y selecciona **Abrir estudio**.")
        st.stop()

    if len(password) < 10:
        st.error("Revisa la clave de acceso.")
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
        st.error("No fue posible abrir el estudio. Revisa el archivo y la clave de acceso.")
        st.stop()
    except Exception:
        st.error("No fue posible abrir el estudio. Revisa el archivo y la clave de acceso.")
        st.stop()

# From here on, only the analytical dataframe and metadata live in session memory.
# The password is no longer needed after decryption.
st.session_state.pop("unlock_password", None)
df = st.session_state["dataset"]
meta = st.session_state["metadata"]

with st.sidebar:
    st.success("Estudio abierto")
    if st.button("Cerrar estudio", use_container_width=True):
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
st.sidebar.markdown(f"**Base seleccionada:** {n} entrevistas")

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
        help="Úsala cuando la base del producto sea pequeña para obtener una lectura más estable.",
    )
    st.sidebar.caption("Observada = dato directo. Tendencial = lectura ajustada para bases pequeñas.")
elif n < 30:
    st.error("La selección actual tiene pocos casos. Elige un solo producto para habilitar la lectura tendencial.")
    st.stop()

if n < 10:
    st.error("La selección actual no tiene suficientes entrevistas para mostrar resultados.")
    st.stop()

is_tendential = reading_mode == "Tendencial" and reference is not None and len(reference) > 0

if is_tendential:
    st.info(
        f"**Lectura tendencial · {n} entrevistas.** "
        "Se muestra una lectura ajustada para reducir la variación asociada a bases pequeñas."
    )

NAV_ITEMS = [
    ("Resumen", ":material/bar_chart:", "Resumen"),
    ("Cómo se decide", ":material/account_tree:", "Cómo se decide"),
    ("Qué pesa más", ":material/diamond:", "Qué pesa más"),
    ("Qué pasa si falta...", ":material/warning:", "Qué pasa si falta..."),
    ("Cómo ordenar el anaquel", ":material/view_module:", "Cómo ordenar el anaquel"),
]

if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "Resumen"

st.markdown('<div class="nav-kicker">EXPLORA EL ESTUDIO</div>', unsafe_allow_html=True)
st.markdown('<div class="nav-title">¿Qué quieres explorar?</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="nav-subtitle">Navega por los principales temas del estudio y descubre los hallazgos más relevantes.</div>',
    unsafe_allow_html=True,
)

clicked_page = None
with st.container(key="study_nav"):
    nav_cols = st.columns([1, 0.12, 1, 0.12, 1, 0.12, 1, 0.12, 1], gap="small")

    for idx, (page_name, page_icon, page_label) in enumerate(NAV_ITEMS):
        col_idx = idx * 2
        is_active = st.session_state["nav_page"] == page_name

        with nav_cols[col_idx]:
            if st.button(
                page_label,
                key=f"nav_card_{idx}",
                icon=page_icon,
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                clicked_page = page_name

            status = "ESTÁS AQUÍ" if is_active else str(idx + 1)
            status_class = "nav-status active" if is_active else "nav-status"
            st.markdown(
                f'<div class="{status_class}">{status}</div>',
                unsafe_allow_html=True,
            )

        if idx < len(NAV_ITEMS) - 1:
            with nav_cols[col_idx + 1]:
                st.markdown(
                    '<div class="nav-connector"><div class="nav-connector-line"></div></div>',
                    unsafe_allow_html=True,
                )

if clicked_page is not None and clicked_page != st.session_state["nav_page"]:
    st.session_state["nav_page"] = clicked_page
    st.rerun()

page = st.session_state["nav_page"]

st.markdown(
    '''
    <div class="nav-guide">
      <div class="nav-guide-icon">
        <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="8" fill="none" stroke="#8098B0" stroke-width="1.7"/>
          <path d="M14.8 9.2l-1.7 4-4 1.7 1.7-4 4-1.7z" fill="none" stroke="#8098B0" stroke-width="1.7" stroke-linejoin="round"/>
        </svg>
      </div>
      <div>Cada sección te permite profundizar en el proceso de decisión, los factores de elección y las oportunidades en anaquel.</div>
    </div>
    ''',
    unsafe_allow_html=True,
)

if page == "Resumen":
    st.markdown("### Resumen ejecutivo")
    st.caption("Una lectura rápida de qué consideran, qué genera valor y qué puede cambiar su elección.")
    k = tendential_kpis(filtered, reference) if is_tendential else executive_kpis(filtered)

    if is_tendential:
        stage = decision_stage_tendential(filtered, reference).rename(columns={"tendencial": "porcentaje"})
    else:
        stage = decision_stage_summary(filtered).rename(columns={"pct": "porcentaje"})
    st.markdown(
        f'<div class="base-strip">'
        f'<span class="base-pill">Base: {n} entrevistas</span>'
        f'<span>La secuencia declarada describe la compra para <b>{k["validacion_arbol"]:.1f}%</b> de los entrevistados.</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    stage_map = {}
    for stage_name in ["Primero", "Después", "Cierre"]:
        temp = (
            stage[stage["etapa"] == stage_name]
            .sort_values("porcentaje", ascending=False)
            .head(3)
        )
        stage_map[stage_name] = [
            (str(r["criterio"]), float(r["porcentaje"])) for _, r in temp.iterrows()
        ]

    cards_html = (
        '<div class="exec-grid">'
        + executive_stage_card(
            1,
            "Lo primero que se decide",
            "Top 3 de criterios que aparecen primero al comenzar la elección.",
            stage_map.get("Primero", []),
            "hair",
            "#1D5E9E",
            "#E8F3FC",
        )
        + executive_stage_card(
            2,
            "Lo que se toma en cuenta después",
            "Top 3 de criterios que aparecen en el segundo momento.",
            stage_map.get("Después", []),
            "diamond",
            "#5B4AE6",
            "#F0EDFF",
        )
        + executive_stage_card(
            3,
            "Lo que termina definiendo la compra",
            "Top 3 de criterios que cierran la decisión.",
            stage_map.get("Cierre", []),
            "check",
            "#169B62",
            "#E8F8F0",
        )
        + '</div>'
    )
    st.markdown(cards_html, unsafe_allow_html=True)

    alcance = decision_reach(stage).head(6).copy()

    if is_tendential:
        md = maxdiff_tendential(filtered, reference).head(5).copy()
        md["valor"] = md["tendencial"]
    else:
        md = maxdiff_compare(filtered, df).head(5).copy()
        md["valor"] = md["segmento"]

    dynamic_insights = get_cached_dynamic_insights(
        filters,
        reading_mode,
        n,
        alcance,
        md,
        k,
    )

    st.markdown(
        '<div class="summary-grid">'
        + reach_panel_html(alcance, dynamic_insights["reach"])
        + drivers_panel_html(md, dynamic_insights["drivers"])
        + substitution_panel_html(k, dynamic_insights["substitution"])
        + '</div>',
        unsafe_allow_html=True,
    )

    top_driver = md.sort_values("valor", ascending=False).iloc[0]
    brand_risk = float(k["cambia_marca_si_falta_marca"])
    promo_resist = float(k["compra_sin_promocion"])

    st.markdown(
        '<div class="implications">'
        '<div class="implications-title">Implicaciones clave</div>'
        '<div class="imp-grid">'
        '<div class="imp-card">'
        f'<div class="imp-kicker">1 · Proteger</div>'
        f'<div class="imp-main">{icon_svg("shield", "#1D5E9E")} Disponibilidad de marca y amplitud de tonos</div>'
        f'<div class="imp-note">El cambio de marca ante falta de disponibilidad alcanza {brand_risk:.1f}%.</div>'
        '</div>'
        '<div class="imp-card">'
        f'<div class="imp-kicker">2 · Comunicar</div>'
        f'<div class="imp-main">{icon_svg("megaphone", "#169B62")} {html.escape(str(top_driver["driver"]))}</div>'
        '<div class="imp-note">Reforzar los beneficios que más valor aportan al elegir.</div>'
        '</div>'
        '<div class="imp-card">'
        f'<div class="imp-kicker">3 · Activar</div>'
        f'<div class="imp-main">{icon_svg("tag", "#5B4AE6")} Promoción como acelerador</div>'
        f'<div class="imp-note">{promo_resist:.1f}% compraría aun sin promoción; funciona mejor como apoyo que como fundamento de la elección.</div>'
        '</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

elif page == "Cómo se decide":
    st.markdown("### Árbol de decisión")
    st.caption(
        "Conservamos la estructura de árbol. La diferencia es que cada porcentaje se lee dentro de su propia rama: no multiplicamos toda la ruta."
    )

    base_reference = reference if is_tendential else filtered

    first_choices = ["Todos"] + options_for(filtered, "decision_1")
    selected_first = st.selectbox(
        "Mostrar el árbol desde:",
        first_choices,
        index=0,
        key="tree_first_choice",
    )
    detail = st.select_slider(
        "Nivel de detalle",
        options=["Simple", "Medio", "Amplio"],
        value="Medio",
    )
    if detail == "Simple":
        top_d1, top_d2, top_d3 = 3, 2, 2
    elif detail == "Amplio":
        top_d1, top_d2, top_d3 = 4, 4, 3
    else:
        top_d1, top_d2, top_d3 = 3, 3, 2

    tree_fig = decision_tree_figure(
        filtered,
        base_reference,
        first_choice=None if selected_first == "Todos" else selected_first,
        force_tendential=is_tendential,
        top_d1=top_d1,
        top_d2=top_d2,
        top_d3=top_d3,
    )
    st.plotly_chart(tree_fig, use_container_width=True)

    st.info(
        "Cómo leer el árbol: el porcentaje entre dos nodos responde a **qué proporción de quienes llegaron al nodo anterior pasa al siguiente criterio**. "
        "Por ejemplo, 20% en Tono → Precio significa 20% de quienes empiezan por Tono pasan después a Precio."
    )

    st.markdown("#### Explora una rama paso a paso")
    st.caption("Selecciona un criterio para ver el detalle detrás de las ramas del árbol.")

    # PASO 1
    if is_tendential:
        step1 = categorical_tendential(
            filtered,
            base_reference,
            "decision_1",
            strength=12.0,
            label_name="opcion",
        )[["opcion", "tendencial"]].rename(columns={"tendencial": "porcentaje"})
        mode1 = "Tendencial"
    else:
        counts1 = filtered["decision_1"].dropna().value_counts()
        step1 = pd.DataFrame({
            "opcion": counts1.index.astype(str),
            "porcentaje": counts1.values / counts1.sum() * 100,
        })
        mode1 = "Observada"

    first_options = step1["opcion"].tolist()
    default_first = selected_first if selected_first != "Todos" and selected_first in first_options else first_options[0]
    first = st.selectbox(
        "Primero:",
        first_options,
        index=first_options.index(default_first),
        key="decision_first",
    )

    target_1 = filtered[filtered["decision_1"] == first].copy()
    ref_1 = base_reference[base_reference["decision_1"] == first].copy()
    step2, mode2, base2 = conditional_reading(
        target_1,
        ref_1,
        base_reference,
        "decision_2",
        force_tendential=is_tendential,
        strength=14.0,
    )

    st.markdown(f"**Después de {first}:**")
    st.caption(f"Base de esta rama: {base2} entrevistas")
    st.plotly_chart(
        conditional_bar(step2, f"Qué viene después de {first}", top_n=8),
        use_container_width=True,
    )

    second_options = step2["opcion"].tolist()
    if second_options:
        second = st.selectbox(
            "Después:",
            second_options,
            index=0,
            key="decision_second",
        )

        target_12 = target_1[target_1["decision_2"] == second].copy()
        ref_12 = ref_1[ref_1["decision_2"] == second].copy()
        broader_d3_ref = ref_1 if len(ref_1) else base_reference

        step3, mode3, base3 = conditional_reading(
            target_12,
            ref_12,
            broader_d3_ref,
            "decision_3",
            force_tendential=is_tendential,
            strength=12.0,
        )

        st.markdown(f"**Cierre después de {first} → {second}:**")
        st.caption(f"Base de esta rama: {base3} entrevistas")
        st.plotly_chart(
            conditional_bar(step3, "Qué termina definiendo la compra", top_n=8),
            use_container_width=True,
        )

    st.caption(
        "El árbol mantiene D1 → D2 → D3. Los porcentajes se calculan de forma condicional en cada bifurcación y por eso no se hacen artificialmente pequeños por multiplicar toda la ruta."
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
        st.caption("La lectura tendencial ayuda a comparar estos factores cuando la base del producto es pequeña.")
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
    st.caption("Ejemplo: “42.0% · 420” equivale a 420 de cada 1,000 compradores bajo el patrón seleccionado.")

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

    st.caption("Esta lectura permite comparar qué formas de organización resultan más útiles para encontrar el producto.")

