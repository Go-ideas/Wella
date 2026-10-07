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
    SHELF_BOOTSTRAP_REPS,
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
    shelf_statistical_model,
    shelf_conditional_model,
    friction_summary,
)
from secure_io import (
    MAGIC,
    VERSION,
    VERSION_MULTI,
    EncryptedPackageError,
    decrypt_sqlite_bytes,
    package_fingerprint,
    sqlite_connection_from_bytes,
)
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

st.set_page_config(
    page_title="Wella | Decision Simulator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
[data-testid="stDecoration"] {display:none !important;}
[data-testid="stStatusWidget"] {visibility:hidden;}
section[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div:first-child {
    background:linear-gradient(180deg,#F8FBFE 0%,#F2F6FA 100%);
    border-right:1px solid #DDE6EF;
}
[data-testid="stSidebarCollapsedControl"] {
    visibility:visible !important;
    opacity:1 !important;
}
[data-testid="stSidebar"] .block-container {
    padding-top:1.1rem !important;
}
.sidebar-hero {
    background:linear-gradient(145deg,#0B3156,#174F7D);
    color:#FFFFFF;
    border-radius:20px;
    padding:18px 17px 16px 17px;
    margin:2px 0 14px 0;
    box-shadow:0 10px 24px rgba(16,55,92,.12);
}
.sidebar-kicker {
    font-size:.68rem;
    letter-spacing:.18em;
    font-weight:800;
    opacity:.75;
    margin-bottom:7px;
}
.sidebar-title-row {
    display:flex;
    align-items:center;
    gap:11px;
}
.sidebar-icon {
    width:38px;
    height:38px;
    border-radius:12px;
    background:rgba(255,255,255,.13);
    display:flex;
    align-items:center;
    justify-content:center;
    flex:0 0 auto;
}
.sidebar-title {
    font-size:1.38rem;
    font-weight:800;
    line-height:1.05;
}
.sidebar-copy {
    margin-top:9px;
    font-size:.82rem;
    line-height:1.38;
    opacity:.84;
}
.sidebar-status-card {
    border:1px solid #CDE8D7;
    background:linear-gradient(180deg,#F1FBF5,#E7F7EE);
    border-radius:15px;
    padding:11px 13px;
    margin:0 0 10px 0;
    display:flex;
    align-items:center;
    gap:9px;
    color:#21683E;
}
.sidebar-status-dot {
    width:9px;height:9px;border-radius:50%;background:#34A56A;box-shadow:0 0 0 4px rgba(52,165,106,.12);
}
.sidebar-status-main {font-size:.84rem;font-weight:800;}
.sidebar-status-sub {font-size:.7rem;color:#5C7A68;margin-top:1px;}
.filter-section-label {
    font-size:.69rem;
    letter-spacing:.10em;
    font-weight:800;
    color:#7890A8;
    text-transform:uppercase;
    margin:14px 0 6px 1px;
}
.filter-summary-card {
    margin:14px 0 8px 0;
    padding:12px 13px;
    border-radius:15px;
    background:#FFFFFF;
    border:1px solid #DCE6EF;
    box-shadow:0 3px 10px rgba(22,56,88,.04);
}
.filter-summary-top {
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:8px;
}
.filter-summary-label {font-size:.72rem;color:#74889D;}
.filter-summary-value {font-size:1rem;font-weight:800;color:#173A5E;}
.filter-summary-note {font-size:.7rem;color:#8294A8;margin-top:4px;}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background:#FFFFFF !important;
    border:1px solid #D9E4EE !important;
    border-radius:13px !important;
    min-height:45px !important;
    box-shadow:0 2px 7px rgba(23,58,94,.025);
}
[data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {
    border-color:#2E7FBE !important;
    box-shadow:0 0 0 3px rgba(46,127,190,.10) !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] {
    background:#E9F3FC !important;
    color:#155A91 !important;
    border-radius:9px !important;
}
[data-testid="stSidebar"] label p {
    color:#17324E !important;
    font-size:.84rem !important;
    font-weight:700 !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button {
    border-radius:12px !important;
}
.sidebar-divider {
    height:1px;background:#DDE6EF;margin:13px 0 10px 0;
}
.footer-credit {
    margin-top:28px;
    padding-top:14px;
    border-top:1px solid #E3E9EF;
    display:flex;
    align-items:flex-end;
    justify-content:space-between;
    gap:16px;
    color:#8A98A6;
    font-size:.72rem;
}
.footer-credit-left {
    color:#8D99A6;
}
.footer-credit-right {
    text-align:right;
    line-height:1.15;
    opacity:.72;
}
.footer-credit-kicker {
    font-size:.60rem;
    letter-spacing:.08em;
    text-transform:uppercase;
    margin-bottom:3px;
}
.footer-credit-brand {
    font-size:.78rem;
    font-weight:700;
    color:#687887;
    letter-spacing:.015em;
}
.block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1500px;}
[data-testid="stMetric"] {background: #F7F9FC; border: 1px solid #E3E8EF; padding: 12px; border-radius: 14px;}
.small-note {font-size: .82rem; color: #667085;}
.brand-shell {
    display:grid;
    grid-template-columns:178px minmax(0,1fr);
    border-radius:22px;
    overflow:hidden;
    margin-bottom:14px;
    border:1px solid #DCE5EE;
    background:#FFFFFF;
}
.brand-rail {
    background:#F2F2F2;
    color:#173A5E;
    padding:14px 14px 13px 14px;
    display:flex;
    flex-direction:column;
    justify-content:center;
    align-items:center;
    min-height:132px;
    text-align:center;
    border-right:1px solid #E1E6EB;
}
.brand-official-logo-frame {
    width:154px;
    height:88px;
    overflow:hidden;
    display:flex;
    align-items:flex-start;
    justify-content:center;
    margin-bottom:7px;
}
.brand-official-logo {
    width:164px;
    max-width:none;
    display:block;
    transform:translateY(-31px);
}
.brand-tag {
    width:100%;
    font-size:.61rem;
    line-height:1.28;
    color:#37546F;
    font-weight:700;
    margin-top:4px;
    letter-spacing:.035em;
}
.brand-main {
    padding:22px 28px 18px 28px;
    display:flex;
    flex-direction:column;
    justify-content:center;
    min-width:0;
    position:relative;
}
.brand-topline {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:18px;
    margin-bottom:2px;
}
.brand-partner {
    font-size:.72rem;
    font-weight:700;
    letter-spacing:.015em;
    color:#7B8B9A;
    opacity:.78;
    white-space:nowrap;
    pointer-events:none;
    user-select:none;
    cursor:default;
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
.decision-header{border:1px solid #DCE6EF;border-radius:20px;background:linear-gradient(180deg,#FFF 0%,#FBFDFF 100%);padding:18px 20px;margin:6px 0 14px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:center;box-shadow:0 5px 16px rgba(22,56,88,.035)}
.decision-header-main{display:flex;align-items:center;gap:14px;min-width:0}
.decision-header-icon{width:54px;height:54px;border-radius:16px;background:#E8F3FC;color:#1D6FB5;display:flex;align-items:center;justify-content:center;flex:0 0 auto}
.decision-header-kicker{font-size:.70rem;letter-spacing:.11em;font-weight:800;color:#7890A8;text-transform:uppercase;margin-bottom:4px}
.decision-header-title{font-size:1.55rem;line-height:1.08;font-weight:800;color:#12365A;margin-bottom:4px}
.decision-header-sub{font-size:.88rem;color:#708399;line-height:1.35}
.decision-meta{display:flex;align-items:stretch;gap:10px}
.decision-meta-card{min-width:120px;border:1px solid #E0E9F1;background:#F7FAFD;border-radius:14px;padding:10px 12px}
.decision-meta-label{font-size:.66rem;color:#7B90A6;margin-bottom:3px}
.decision-meta-value{font-size:.98rem;font-weight:800;color:#173A5E}
.decision-steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-bottom:14px}
.decision-step-card{border:1px solid #DCE6EF;border-radius:18px;background:#FFF;padding:15px 16px;min-height:148px;display:grid;grid-template-columns:48px minmax(0,1fr) auto;gap:12px;align-items:center;box-shadow:0 4px 14px rgba(22,56,88,.035)}
.decision-step-icon{width:46px;height:46px;border-radius:50%;display:flex;align-items:center;justify-content:center}
.decision-step-kicker{font-size:.69rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#758AA1;margin-bottom:5px}
.decision-step-name{font-size:1rem;line-height:1.2;font-weight:800;color:#173A5E}
.decision-step-copy{font-size:.72rem;color:#8090A2;line-height:1.3;margin-top:4px}
.decision-step-value{font-size:1.42rem;font-weight:800;color:#0F65AA;white-space:nowrap;text-align:right}
.st-key-decision_tree_panel [data-testid="stVerticalBlockBorderWrapper"],.st-key-decision_insight_panel [data-testid="stVerticalBlockBorderWrapper"],.st-key-decision_route_panel [data-testid="stVerticalBlockBorderWrapper"],.st-key-decision_reading_panel [data-testid="stVerticalBlockBorderWrapper"]{border:1px solid #DCE6EF!important;border-radius:20px!important;background:#FFF!important;box-shadow:0 5px 16px rgba(22,56,88,.035)}
.decision-tree-title{font-size:1.10rem;font-weight:800;color:#153A60}.decision-tree-sub{font-size:.78rem;color:#74889D;margin-top:2px}.decision-insight-text{font-size:.88rem;line-height:1.5;color:#2B4863;background:#F7FAFD;border:1px solid #E5EDF4;border-radius:14px;padding:13px 14px}
.route-flow{display:grid;grid-template-columns:1fr 22px 1fr 22px 1fr;gap:6px;align-items:center;margin-top:10px}.route-node{border:1px solid #DCE6EF;background:#F8FBFE;border-radius:14px;padding:10px;text-align:center;min-width:0}.route-node-label{font-size:.66rem;color:#788DA3;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px}.route-node-name{font-size:.78rem;line-height:1.2;font-weight:800;color:#173A5E;overflow-wrap:anywhere}.route-node-value{font-size:.86rem;font-weight:800;color:#0F68B2;margin-top:3px}.route-arrow{color:#8AA6BF;font-size:1.1rem;text-align:center}
.decision-section-title{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;margin:16px 0 10px}
.decision-section-title-main{font-size:1.18rem;font-weight:800;color:#153A60}
.decision-section-title-sub{font-size:.78rem;color:#75899F;margin-top:3px}
.st-key-decision_controls [data-testid="stVerticalBlockBorderWrapper"]{border:1px solid #DCE6EF!important;border-radius:17px!important;background:#FAFCFE!important;padding:4px 8px 8px!important}
.st-key-decision_controls label p{font-size:.72rem!important;font-weight:800!important;color:#44627F!important}
.st-key-decision_controls [data-testid="stSegmentedControl"] button{min-height:38px!important;font-size:.78rem!important;font-weight:700!important}
.decision-side-title{font-size:1.03rem;font-weight:800;color:#153A60;margin-bottom:4px}
.decision-side-sub{font-size:.72rem;color:#7A8EA4;margin-bottom:12px}
.main-route-vertical{display:flex;flex-direction:column;gap:0;margin-top:4px}
.main-route-step{display:grid;grid-template-columns:34px minmax(0,1fr);gap:10px;align-items:center;padding:8px 0}
.main-route-number{width:30px;height:30px;border-radius:50%;background:#2F80ED;color:#FFF;display:flex;align-items:center;justify-content:center;font-size:.78rem;font-weight:800}
.main-route-name{font-size:.82rem;font-weight:800;color:#173A5E;line-height:1.2}
.main-route-pct{font-size:1rem;font-weight:800;color:#1871C7;margin-top:2px}
.main-route-connector{width:2px;height:14px;background:#BDD1E4;margin-left:14px}
.alt-routes{margin-top:12px;padding-top:12px;border-top:1px solid #E6EDF4}
.alt-route-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;padding:9px 0;border-bottom:1px solid #EEF2F6}
.alt-route-name{font-size:.72rem;line-height:1.32;color:#506A84}
.alt-route-pct{font-size:.78rem;font-weight:800;color:#173A5E}
.reading-card-title{font-size:1rem;font-weight:800;color:#153A60;margin-bottom:6px}
.reading-card-copy{font-size:.80rem;line-height:1.48;color:#5F7489}
.reading-card-copy ul{margin:.15rem 0 0 1.1rem;padding:0}
.reading-card-copy li{margin:.18rem 0}
.decision-explore-panel{border:1px solid #DCE6EF;background:#F8FBFE;border-radius:16px;padding:12px 14px;margin:10px 0 12px}
.decision-explore-kicker{font-size:.68rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#7590AA;margin-bottom:3px}
.decision-explore-copy{font-size:.78rem;color:#668097;line-height:1.35}
.decision-dynamic-insight{margin-top:12px;border:1px solid #DCE6EF;background:linear-gradient(90deg,#F7FBFF,#FFFFFF);border-radius:16px;padding:13px 15px;font-size:.84rem;line-height:1.45;color:#35516E}
.decision-dynamic-insight b{color:#153A60}
.tree-column-heads{
    display:grid;
    grid-template-columns:.72fr 1fr 1fr 1fr;
    gap:26px;
    align-items:stretch;
    margin:12px 8px 18px 8px;
}
.tree-column-head{
    background:#F3F7FB;
    border:1px solid #E7EEF5;
    border-radius:12px;
    padding:10px 12px 9px;
    text-align:center;
}
.tree-column-title{
    font-size:.80rem;
    font-weight:800;
    color:#35516E;
    line-height:1.15;
}
.tree-column-sub{
    margin-top:4px;
    font-size:.66rem;
    color:#8092A6;
    line-height:1.2;
}
@media(max-width:900px){
    .tree-column-heads{gap:8px;grid-template-columns:.72fr 1fr 1fr 1fr}
    .tree-column-head{padding:8px 6px}
    .tree-column-sub{display:none}
}
@media (max-width:900px){.decision-section-title{align-items:flex-start;flex-direction:column}.main-route-step{grid-template-columns:30px minmax(0,1fr)}}
@media (max-width:900px){.decision-header{grid-template-columns:1fr}.decision-meta{width:100%}.decision-meta-card{flex:1}.decision-steps{grid-template-columns:1fr}.route-flow{grid-template-columns:1fr}.route-arrow{transform:rotate(90deg)}}
.drivers-header{
    border:1px solid #DCE6EF;
    border-radius:20px;
    background:linear-gradient(180deg,#FFFFFF 0%,#FBFDFF 100%);
    padding:18px 20px;
    margin:6px 0 14px;
    display:grid;
    grid-template-columns:minmax(0,1fr) auto;
    gap:20px;
    align-items:center;
    box-shadow:0 5px 16px rgba(22,56,88,.035);
}
.drivers-header-main{display:flex;align-items:center;gap:14px;min-width:0}
.drivers-header-icon{width:54px;height:54px;border-radius:16px;background:#EEF4FF;display:flex;align-items:center;justify-content:center;flex:0 0 auto}
.drivers-header-kicker{font-size:.70rem;letter-spacing:.11em;font-weight:800;color:#7890A8;text-transform:uppercase;margin-bottom:4px}
.drivers-header-title{font-size:1.55rem;line-height:1.08;font-weight:800;color:#12365A;margin-bottom:4px}
.drivers-header-sub{font-size:.88rem;color:#708399;line-height:1.35}
.drivers-meta{min-width:145px;border:1px solid #E0E9F1;background:#F7FAFD;border-radius:14px;padding:10px 12px}
.drivers-meta-label{font-size:.66rem;color:#7B90A6;margin-bottom:3px}
.drivers-meta-value{font-size:.98rem;font-weight:800;color:#173A5E}
.driver-top-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:0 0 14px}
.driver-top-card{border:1px solid #DCE6EF;border-radius:18px;background:#FFF;padding:15px 16px;min-height:120px;display:grid;grid-template-columns:42px minmax(0,1fr) auto;gap:12px;align-items:center;box-shadow:0 4px 14px rgba(22,56,88,.035)}
.driver-rank{width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.82rem;font-weight:800;background:#E8F3FC;color:#1D6FB5}
.driver-card-kicker{font-size:.66rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#758AA1;margin-bottom:5px}
.driver-card-name{font-size:.94rem;line-height:1.2;font-weight:800;color:#173A5E}
.driver-card-value{font-size:1.32rem;font-weight:800;color:#0F65AA;white-space:nowrap;text-align:right}
.driver-card-note{font-size:.68rem;color:#8090A2;margin-top:5px;line-height:1.25}
.st-key-driver_chart_panel [data-testid="stVerticalBlockBorderWrapper"],
.st-key-driver_insight_panel [data-testid="stVerticalBlockBorderWrapper"]{
    border:1px solid #DCE6EF!important;
    border-radius:20px!important;
    background:#FFF!important;
    box-shadow:0 5px 16px rgba(22,56,88,.035);
}
.driver-panel-title{font-size:1.08rem;font-weight:800;color:#153A60}
.driver-panel-sub{font-size:.78rem;color:#74889D;margin-top:2px;margin-bottom:4px}
.driver-insight{border:1px solid #DCE6EF;background:linear-gradient(90deg,#F7FBFF,#FFFFFF);border-radius:16px;padding:13px 15px;font-size:.84rem;line-height:1.48;color:#35516E}
.driver-insight b{color:#153A60}
.risk-header{
    border:1px solid #DCE6EF;
    border-radius:20px;
    background:linear-gradient(180deg,#FFFFFF 0%,#FBFDFF 100%);
    padding:18px 20px;
    margin:6px 0 14px;
    display:grid;
    grid-template-columns:minmax(0,1fr) auto;
    gap:20px;
    align-items:center;
    box-shadow:0 5px 16px rgba(22,56,88,.035);
}
.risk-header-main{display:flex;align-items:center;gap:14px;min-width:0}
.risk-header-icon{width:54px;height:54px;border-radius:16px;background:#FFF1F3;display:flex;align-items:center;justify-content:center;flex:0 0 auto}
.risk-header-kicker{font-size:.70rem;letter-spacing:.11em;font-weight:800;color:#7890A8;text-transform:uppercase;margin-bottom:4px}
.risk-header-title{font-size:1.55rem;line-height:1.08;font-weight:800;color:#12365A;margin-bottom:4px}
.risk-header-sub{font-size:.88rem;color:#708399;line-height:1.35}
.risk-meta{min-width:145px;border:1px solid #E0E9F1;background:#F7FAFD;border-radius:14px;padding:10px 12px}
.risk-meta-label{font-size:.66rem;color:#7B90A6;margin-bottom:3px}
.risk-meta-value{font-size:.98rem;font-weight:800;color:#173A5E}
.risk-kpi-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-bottom:14px}
.risk-kpi-card{border:1px solid #DCE6EF;border-radius:18px;background:#FFF;padding:16px 17px;min-height:138px;display:flex;flex-direction:column;justify-content:space-between;box-shadow:0 4px 14px rgba(22,56,88,.035)}
.risk-kpi-top{display:flex;align-items:center;gap:10px}
.risk-kpi-icon{width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex:0 0 auto}
.risk-kpi-label{font-size:.78rem;font-weight:800;color:#173A5E;line-height:1.2}
.risk-kpi-value{font-size:1.62rem;font-weight:800;line-height:1;color:#153A60;margin-top:12px}
.risk-kpi-note{font-size:.72rem;line-height:1.35;color:#7A8EA4;margin-top:6px}
.st-key-risk_sim_panel [data-testid="stVerticalBlockBorderWrapper"],
.st-key-risk_insight_panel [data-testid="stVerticalBlockBorderWrapper"]{
    border:1px solid #DCE6EF!important;
    border-radius:20px!important;
    background:#FFF!important;
    box-shadow:0 5px 16px rgba(22,56,88,.035);
}
.risk-panel-title{font-size:1.08rem;font-weight:800;color:#153A60}
.risk-panel-sub{font-size:.78rem;color:#74889D;margin-top:2px;margin-bottom:8px}
.risk-insight{border:1px solid #DCE6EF;background:linear-gradient(90deg,#FFF8F9,#FFFFFF);border-radius:16px;padding:13px 15px;font-size:.84rem;line-height:1.5;color:#35516E}
.risk-insight b{color:#153A60}
.shelf-header{
    border:1px solid #DCE6EF;
    border-radius:20px;
    background:linear-gradient(180deg,#FFFFFF 0%,#FBFDFF 100%);
    padding:18px 20px;
    margin:6px 0 14px;
    display:grid;
    grid-template-columns:minmax(0,1fr) auto;
    gap:20px;
    align-items:center;
    box-shadow:0 5px 16px rgba(22,56,88,.035);
}
.shelf-header-main{display:flex;align-items:center;gap:14px;min-width:0}
.shelf-header-icon{width:54px;height:54px;border-radius:16px;background:#EEF7FF;display:flex;align-items:center;justify-content:center;flex:0 0 auto}
.shelf-header-kicker{font-size:.70rem;letter-spacing:.11em;font-weight:800;color:#7890A8;text-transform:uppercase;margin-bottom:4px}
.shelf-header-title{font-size:1.55rem;line-height:1.08;font-weight:800;color:#12365A;margin-bottom:4px}
.shelf-header-sub{font-size:.88rem;color:#708399;line-height:1.35}
.shelf-meta{min-width:145px;border:1px solid #E0E9F1;background:#F7FAFD;border-radius:14px;padding:10px 12px}
.shelf-meta-label{font-size:.66rem;color:#7B90A6;margin-bottom:3px}
.shelf-meta-value{font-size:.98rem;font-weight:800;color:#173A5E}
.shelf-top-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-bottom:14px}
.shelf-top-card{
    border:1px solid #DCE6EF;
    border-radius:18px;
    background:linear-gradient(180deg,#FFFFFF 0%,#FBFDFF 100%);
    padding:16px 16px 14px;
    min-height:146px;
    display:flex;
    flex-direction:column;
    justify-content:space-between;
    box-shadow:0 4px 14px rgba(22,56,88,.035)
}
.shelf-top-card:first-child{
    border-color:#A9CFEF;
    background:linear-gradient(180deg,#F7FBFF 0%,#EEF7FF 100%);
    box-shadow:0 8px 22px rgba(29,118,190,.08)
}
.shelf-card-topline{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.shelf-card-titlewrap{display:flex;align-items:center;gap:10px;min-width:0}
.shelf-rank{
    width:36px;height:36px;border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    font-size:.80rem;font-weight:800;background:#E8F3FC;color:#1D6FB5;flex:0 0 auto
}
.shelf-top-card:first-child .shelf-rank{background:#1D76BE;color:#FFF}
.shelf-card-kicker{font-size:.64rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#758AA1;margin-bottom:4px}
.shelf-card-name{font-size:.94rem;line-height:1.2;font-weight:800;color:#173A5E}
.shelf-card-value{font-size:1.52rem;font-weight:800;color:#0F65AA;white-space:nowrap;text-align:right;line-height:1}
.shelf-card-metrics{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}
.shelf-card-chip{
    display:inline-flex;align-items:center;gap:4px;
    border-radius:999px;padding:5px 8px;
    background:#F4F8FB;border:1px solid #DFE8F0;
    font-size:.63rem;color:#60778D;font-weight:700
}
.shelf-card-chip strong{color:#173A5E}
.shelf-prob-explainer{
    border:1px solid #DCE6EF;
    background:linear-gradient(90deg,#F7FBFF,#FFFFFF);
    border-radius:16px;
    padding:12px 14px;
    margin:0 0 14px;
    display:flex;
    align-items:flex-start;
    gap:10px;
}
.shelf-prob-explainer-main{
    font-size:.80rem;
    line-height:1.4;
    color:#35516E;
}
.shelf-prob-explainer-main b{color:#153A60}
.shelf-prob-explainer-note{
    margin-top:3px;
    font-size:.67rem;
    color:#7B8FA4;
    line-height:1.3;
}
.st-key-shelf_rank_panel [data-testid="stVerticalBlockBorderWrapper"],
.st-key-shelf_combo_panel [data-testid="stVerticalBlockBorderWrapper"],
.st-key-shelf_friction_panel [data-testid="stVerticalBlockBorderWrapper"]{
    border:1px solid #DCE6EF!important;
    border-radius:20px!important;
    background:#FFF!important;
    box-shadow:0 5px 16px rgba(22,56,88,.035);
}
.shelf-panel-title{font-size:1.08rem;font-weight:800;color:#153A60}
.shelf-panel-sub{font-size:.78rem;color:#74889D;margin-top:2px;margin-bottom:8px}
.shelf-kpi-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:12px}
.shelf-kpi{border:1px solid #E2EAF2;background:#F8FBFE;border-radius:15px;padding:12px 13px}
.shelf-kpi-label{font-size:.68rem;color:#7A8EA4;line-height:1.25}
.shelf-kpi-value{font-size:1.25rem;font-weight:800;color:#153A60;margin-top:4px}
.shelf-ease-box{display:flex;align-items:center;gap:12px;border:1px solid #DCE6EF;background:#F7FBFF;border-radius:16px;padding:14px 15px;margin-bottom:10px}
.shelf-friction-alert{
    border:1px solid #F0D9DC;background:#FFF7F8;border-radius:15px;
    padding:11px 13px;margin:10px 0 12px;
    display:flex;align-items:center;gap:10px
}
.shelf-friction-alert-main{font-size:.78rem;font-weight:800;color:#7D3140;line-height:1.3}
.shelf-friction-alert-sub{font-size:.66rem;color:#9A6570;margin-top:2px}
.shelf-ease-value{font-size:1.55rem;font-weight:800;color:#0F65AA}
.shelf-ease-copy{font-size:.78rem;line-height:1.35;color:#60778D}
.shelf-insight{border:1px solid #DCE6EF;background:linear-gradient(90deg,#F7FBFF,#FFFFFF);border-radius:16px;padding:13px 15px;font-size:.84rem;line-height:1.5;color:#35516E;margin-top:10px}
.shelf-insight b{color:#153A60}
.shelf-mode-note{
    border:1px solid #D7E6F2;
    background:linear-gradient(90deg,#F5FAFE,#FFFFFF);
    border-radius:14px;
    padding:10px 12px;
    margin:10px 0 12px;
    font-size:.72rem;
    line-height:1.42;
    color:#60778D;
}
.shelf-mode-main{font-weight:800;color:#315E84}
.shelf-stat-grid{
    margin-top:12px;
    display:grid;
    grid-template-columns:repeat(3,minmax(0,1fr));
    gap:10px;
}
.shelf-stat-grid.two{grid-template-columns:repeat(2,minmax(0,1fr))}
.shelf-stat-card{
    border:1px solid #E2EAF2;
    border-radius:15px;
    background:#FFF;
    padding:12px 13px;
    min-height:112px;
}
.shelf-stat-card.primary{background:#F6FBFF;border-color:#CFE3F4}
.shelf-stat-card.secondary{background:#FAF8FF;border-color:#E5DFF8}
.shelf-stat-card.affinity{background:#F8FBF9;border-color:#D9EADF}
.shelf-stat-label{
    font-size:.63rem;
    font-weight:800;
    color:#6F849A;
    text-transform:uppercase;
    letter-spacing:.04em;
}
.shelf-stat-value{
    margin-top:5px;
    font-size:1.30rem;
    font-weight:800;
    color:#173A5E;
    line-height:1
}
.shelf-stat-note{
    margin-top:7px;
    font-size:.65rem;
    line-height:1.34;
    color:#7A8EA4;
}
.shelf-stat-status{
    display:inline-flex;
    margin-top:7px;
    border-radius:999px;
    padding:4px 7px;
    font-size:.60rem;
    font-weight:800;
    background:#EEF4F8;
    color:#58738C
}
.shelf-method-badge{
    display:inline-flex;
    align-items:center;
    gap:6px;
    border-radius:999px;
    padding:6px 9px;
    background:#EEF4FF;
    color:#315F96;
    font-size:.66rem;
    font-weight:800;
}
@media(max-width:900px){
    .shelf-stat-grid,.shelf-stat-grid.two{grid-template-columns:1fr}
}
.shelf-visual-shell{
    margin-top:14px;
    border:1px solid #DCE6EF;
    border-radius:18px;
    background:linear-gradient(180deg,#FCFEFF 0%,#F7FAFD 100%);
    padding:14px 14px 16px;
}
.shelf-visual-top{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    margin-bottom:12px;
}
.shelf-visual-badge{
    display:inline-flex;
    align-items:center;
    gap:8px;
    border-radius:999px;
    padding:8px 12px;
    background:#E8F3FC;
    color:#155E98;
    font-size:.74rem;
    font-weight:800;
}
.shelf-reco-summary{
    display:flex;align-items:center;gap:8px;flex-wrap:wrap
}
.shelf-confidence-pill{
    display:inline-flex;align-items:center;
    border-radius:999px;padding:7px 10px;
    background:#F4F8FB;border:1px solid #DCE6EF;
    color:#60778D;font-size:.67rem;font-weight:700
}
.shelf-visual-help{
    font-size:.70rem;
    color:#7B8FA4;
    text-align:right;
}
.shelf-unit{
    display:grid;
    grid-template-columns:180px minmax(0,1fr);
    gap:12px;
    align-items:stretch;
    margin:8px 0 0;
}
.shelf-unit-label{
    border:1px solid #D5E4F0;
    border-radius:14px;
    background:#F2F8FE;
    padding:11px 12px;
    display:flex;
    align-items:center;
    gap:10px;
}
.shelf-unit-label.secondary{background:#F8F6FF;border-color:#E2DDF8}
.shelf-unit-label.support{background:#F8FAFC;border-color:#E3EAF0}
.shelf-unit-num{
    width:28px;height:28px;border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    flex:0 0 auto;
    background:#1D76BE;color:#fff;font-size:.72rem;font-weight:800;
}
.shelf-unit-label.secondary .shelf-unit-num{background:#6A5ACD}
.shelf-unit-label.support .shelf-unit-num{background:#8497AA}
.shelf-unit-main{
    font-size:.76rem;
    font-weight:800;
    line-height:1.18;
    color:#173A5E;
}
.shelf-unit-sub{
    margin-top:3px;
    font-size:.64rem;
    line-height:1.25;
    color:#7890A7;
}
.shelf-products{
    position:relative;
    border:1px solid #DCE6EF;
    border-radius:14px 14px 8px 8px;
    background:#FFFFFF;
    padding:10px 12px 17px;
    display:grid;
    grid-template-columns:repeat(4,minmax(0,1fr));
    gap:8px;
    align-items:end;
    min-height:88px;
    overflow:hidden;
}
.shelf-products::after{
    content:"";
    position:absolute;
    left:0;right:0;bottom:6px;height:7px;
    background:linear-gradient(180deg,#DCE5EC,#C9D4DD);
    border-radius:4px;
    box-shadow:0 3px 8px rgba(40,75,105,.10);
}
.shelf-product{
    position:relative;
    z-index:1;
    min-height:48px;
    border-radius:10px 10px 4px 4px;
    border:1px solid #D8E3ED;
    background:linear-gradient(180deg,#F5F9FD,#E8F2FA);
    padding:8px 7px;
    display:flex;
    align-items:center;
    justify-content:center;
    text-align:center;
    font-size:.66rem;
    line-height:1.18;
    font-weight:700;
    color:#31506D;
}
.shelf-products.secondary .shelf-product{
    background:linear-gradient(180deg,#F9F7FF,#EEEAFE);
    border-color:#E1DCF7;
}
.shelf-products.support .shelf-product{
    background:linear-gradient(180deg,#FAFCFE,#F0F4F7);
    border-color:#E0E8EF;
}
.shelf-route-grid{
    display:grid;
    grid-template-columns:minmax(0,1fr) 44px minmax(0,1fr) 44px minmax(0,1fr);
    gap:12px;
    align-items:stretch;
    margin-top:14px;
}
.shelf-route-card{
    border:1px solid #DCE6EF;
    border-radius:18px;
    padding:18px;
    background:linear-gradient(180deg,#FFFFFF 0%,#F9FCFF 100%);
    min-height:210px;
}
.shelf-route-card.secondary{
    background:linear-gradient(180deg,#FFFFFF 0%,#FBF9FF 100%);
    border-color:#E2DDF8;
}
.shelf-route-card.tertiary{
    background:linear-gradient(180deg,#FFFFFF 0%,#F8FAFC 100%);
    border-color:#E1E8EF;
}
.shelf-route-card-head{
    display:flex;
    align-items:flex-start;
    gap:12px;
    margin-bottom:16px;
}
.shelf-route-step{
    width:38px;height:38px;border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    flex:0 0 auto;background:#1D76BE;color:#FFF;
    font-size:.86rem;font-weight:800;
}
.shelf-route-card.secondary .shelf-route-step{background:#6A5ACD}
.shelf-route-card.tertiary .shelf-route-step{background:#8295A8}
.shelf-route-kicker{
    font-size:.68rem;font-weight:800;letter-spacing:.06em;
    text-transform:uppercase;color:#7890A7;margin-bottom:4px;
}
.shelf-route-name{
    font-size:1.06rem;font-weight:800;line-height:1.22;color:#173A5E;
}
.shelf-route-explain{
    margin-top:5px;font-size:.78rem;line-height:1.38;color:#6F849A;
}
.shelf-route-metric{
    display:inline-flex;align-items:baseline;gap:5px;
    margin:2px 0 14px 50px;
    font-size:1.15rem;font-weight:800;color:#173A5E;
}
.shelf-route-metric span{
    font-size:.66rem;font-weight:600;color:#7A8EA4;
}
.shelf-route-examples-label{
    font-size:.65rem;font-weight:800;text-transform:uppercase;
    letter-spacing:.05em;color:#8A9CAF;margin-bottom:8px;
}
.shelf-route-chips{
    display:flex;gap:8px;flex-wrap:wrap;
}
.shelf-route-chip{
    padding:8px 10px;border-radius:10px;
    background:#EEF6FC;border:1px solid #D8E8F4;
    color:#31506D;font-size:.72rem;font-weight:700;
}
.shelf-route-card.secondary .shelf-route-chip{
    background:#F5F2FF;border-color:#E2DCF8;
}
.shelf-route-card.tertiary .shelf-route-chip{
    background:#F4F7F9;border-color:#E1E8EF;
}
.shelf-route-arrow{
    display:flex;align-items:center;justify-content:center;
    color:#8AA6BF;font-size:2.2rem;font-weight:300;
}
.shelf-route-bottom{
    display:grid;
    grid-template-columns:.85fr .85fr 1.3fr;
    gap:14px;
    margin-top:14px;
}
.shelf-route-evidence,.shelf-route-meaning{
    border-radius:17px;padding:16px 18px;
    border:1px solid #DCE6EF;background:#FFF;
}
.shelf-route-evidence{
    background:#F8F6FF;border-color:#E2DDF8;
}
.shelf-route-meaning{
    background:#F5FAF7;border-color:#D7E8DE;
}
.shelf-route-label{
    font-size:.66rem;font-weight:800;letter-spacing:.06em;
    text-transform:uppercase;color:#73889D;
}
.shelf-route-big{
    margin-top:4px;font-size:2rem;line-height:1;font-weight:800;color:#173A5E;
}
.shelf-route-copy{
    margin-top:8px;font-size:.79rem;line-height:1.42;color:#61788E;
}
.shelf-route-meaning-main{
    margin-top:6px;font-size:1.05rem;line-height:1.35;font-weight:800;color:#173A5E;
}
.shelf-route-note{
    margin-top:9px;font-size:.68rem;line-height:1.35;color:#7B8FA4;
}
@media(max-width:900px){
    .shelf-route-grid{grid-template-columns:1fr}
    .shelf-route-arrow{transform:rotate(90deg);min-height:24px}
    .shelf-route-bottom{grid-template-columns:1fr}
}
.shelf-visual-summary{
    margin-top:12px;
    display:grid;
    grid-template-columns:1.2fr .8fr .8fr;
    gap:10px;
}
.shelf-visual-summary-card{
    border:1px solid #E2EAF2;
    border-radius:13px;
    background:#FFFFFF;
    padding:10px 11px;
}
.shelf-visual-summary-label{
    font-size:.68rem;
    font-weight:800;
    color:#4E6A84;
    line-height:1.2;
    text-transform:uppercase;
    letter-spacing:.035em;
}
.shelf-visual-summary-value{
    margin-top:5px;
    font-size:1.18rem;
    font-weight:800;
    color:#173A5E;
}
.shelf-visual-summary-note{
    margin-top:5px;
    font-size:.65rem;
    line-height:1.3;
    color:#7A8EA4;
}
@media(max-width:900px){
    .shelf-unit{grid-template-columns:1fr}
    .shelf-products{grid-template-columns:repeat(2,minmax(0,1fr))}
    .shelf-visual-summary{grid-template-columns:1fr}
    .shelf-visual-top{align-items:flex-start;flex-direction:column}
    .shelf-visual-help{text-align:left}
}
@media(max-width:900px){
    .shelf-header{grid-template-columns:1fr}
    .shelf-top-grid,.shelf-kpi-grid{grid-template-columns:1fr}
}
@media(max-width:900px){
    .risk-header{grid-template-columns:1fr}
    .risk-kpi-grid{grid-template-columns:1fr}
}
@media(max-width:900px){
    .drivers-header{grid-template-columns:1fr}
    .driver-top-grid{grid-template-columns:1fr}
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
    font-size:.76rem;
    font-weight:800;
    letter-spacing:.26em;
    color:#7790AA;
    margin-top:10px;
    margin-bottom:6px;
}
.nav-kicker::before,.nav-kicker::after {
    content:"";
    display:inline-block;
    width:38px;
    height:1px;
    background:#B8C9D9;
    vertical-align:middle;
    margin:0 12px;
}
.nav-title {
    text-align:center;
    color:#0A2E55;
    font-size:2rem;
    font-weight:800;
    line-height:1.08;
    margin-bottom:6px;
}
.nav-subtitle {
    text-align:center;
    color:#72859B;
    font-size:.92rem;
    margin-bottom:18px;
}
[class*="st-key-nav_tile_"] {
    min-height:218px;
    border:1px solid #DCE6EF !important;
    border-radius:22px !important;
    background:linear-gradient(180deg,#FFFFFF 0%,#FBFDFF 100%) !important;
    box-shadow:0 8px 24px rgba(24,62,101,.05);
    padding:16px 14px 14px 14px !important;
    position:relative;
    transition:all .18s ease;
}
[class*="st-key-nav_tile_"]:hover {
    transform:translateY(-2px);
    box-shadow:0 12px 28px rgba(24,82,135,.09);
    border-color:#AFCDE8 !important;
}
[class*="st-key-nav_tile_"][class*="_active"] {
    border:2px solid #1B79C8 !important;
    background:linear-gradient(180deg,#F8FCFF 0%,#EDF6FF 100%) !important;
    box-shadow:0 12px 30px rgba(27,121,200,.14);
}
.nav-icon-wrap {
    position:relative;
    display:flex;
    justify-content:center;
    align-items:center;
    margin:2px auto 8px auto;
    min-height:72px;
}
.nav-icon-circle {
    width:66px;
    height:66px;
    border-radius:50%;
    background:#EEF5FB;
    color:#2369A7;
    display:flex;
    align-items:center;
    justify-content:center;
    box-shadow:inset 0 0 0 1px rgba(35,105,167,.05);
}
.nav-icon-circle.active {
    background:linear-gradient(145deg,#0F5CA4,#2586D4);
    color:#FFFFFF;
    box-shadow:0 8px 18px rgba(20,105,177,.20);
}
.nav-icon-circle svg {
    width:34px !important;
    height:34px !important;
}
.nav-step-badge {
    position:absolute;
    top:-2px;
    right:calc(50% - 43px);
    width:23px;
    height:23px;
    border-radius:50%;
    background:#FFFFFF;
    border:1px solid #C9D8E6;
    color:#70879E;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:.69rem;
    font-weight:800;
    z-index:2;
}
[class*="_active"] .nav-step-badge {
    background:#0F68B2;
    border-color:#0F68B2;
    color:#FFFFFF;
}
[class*="st-key-nav_tile_"] [data-testid="stButton"] > button {
    width:100%;
    min-height:40px;
    border:0 !important;
    background:transparent !important;
    box-shadow:none !important;
    padding:4px 6px !important;
    color:#163858 !important;
}
[class*="st-key-nav_tile_"] [data-testid="stButton"] > button:hover {
    border:0 !important;
    background:transparent !important;
    box-shadow:none !important;
    color:#0E67B0 !important;
    transform:none !important;
}
[class*="st-key-nav_tile_"] [data-testid="stButton"] p {
    width:100% !important;
    font-size:1rem !important;
    line-height:1.18 !important;
    font-weight:800 !important;
    text-align:center !important;
    margin:0 !important;
    white-space:normal !important;
}
[class*="_active"] [data-testid="stButton"] p {
    color:#0A5D9F !important;
}
.nav-subline {
    text-align:center;
    color:#7B8EA4;
    font-size:.75rem;
    line-height:1.25;
    min-height:34px;
    padding:0 6px;
    display:flex;
    align-items:center;
    justify-content:center;
}
.nav-status {
    text-align:center;
    margin-top:8px;
    font-size:.72rem;
    font-weight:800;
    letter-spacing:.04em;
    color:#91A2B4;
    min-height:18px;
}
.nav-status.active {
    color:#0C68B5;
}
.nav-guide {
    margin:16px 0 22px 0;
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
@media (max-width: 900px) {
    .brand-main {padding:20px 22px 18px 22px;}
    [class*="st-key-nav_tile_"] {min-height:188px;padding:13px 10px 12px 10px !important;}
    .nav-icon-circle {width:58px;height:58px;}
    .nav-icon-circle svg {width:30px !important;height:30px !important;}
    .nav-title {font-size:1.55rem;}
    .nav-subtitle {font-size:.84rem;}
}
@media (max-width: 1050px) {
    .summary-grid {grid-template-columns:1fr;}
    .brand-shell {grid-template-columns:148px minmax(0,1fr);}
}
@media (max-width: 900px) {
    .st-key-study_nav [data-testid="stHorizontalBlock"] {gap:.45rem !important;}
    .st-key-study_nav [data-testid="stButton"] > button {min-height:112px;font-size:.84rem;}
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
        <div class="brand-official-logo-frame">
          <img
            class="brand-official-logo"
            src="https://s3-eu-west-1.amazonaws.com/wellamymarketing-public/es/detail/6c9e9c12-192d-4b89-995a-b5326b8f2738.jpg"
            alt="Wella"
          />
        </div>
        <div class="brand-tag">DECISIÓN DE COMPRA<br>COLORACIÓN</div>
      </div>
      <div class="brand-main">
        <div class="brand-topline">
          <div class="brand-kicker">Resumen ejecutivo</div>
          <div class="brand-partner">Go-Ideas</div>
        </div>
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
        "route": '<path d="M6 5a2 2 0 1 0 0 .1M6 7v5c0 2 1 3 3 3h6M18 13a2 2 0 1 0 0 .1M18 15v4M18 19a2 2 0 1 0 0 .1" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
        "grid": '<rect x="4" y="4" width="6" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="1.7"/><rect x="14" y="4" width="6" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="1.7"/><rect x="4" y="14" width="6" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="1.7"/><rect x="14" y="14" width="6" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="1.7"/>',
        "brand_missing": '<path d="M4 11V5h6l9 9-5 5-10-8zM8 8h.01M9.5 14.5l5-5M10 10l4 4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"/>',
        "tone_missing": '<path d="M12 3c3.8 4.3 6 7.1 6 10a6 6 0 0 1-12 0c0-2.9 2.2-5.7 6-10zM8.7 13.6c.8 1.7 2 2.5 3.6 2.7" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
        "promo_missing": '<path d="M4 11V5h6l9 9-5 5-10-8zM8 8h.01M9 15l6-6M10 10h.01M14 14h.01" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"/>',
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


def main_decision_path(
    data: pd.DataFrame,
    reference_data: pd.DataFrame,
    *,
    force_tendential: bool = False,
) -> dict:
    """Ruta principal D1 → D2 → D3 usando la misma lectura condicional del árbol."""
    step1, mode1, base1 = conditional_reading(
        data,
        reference_data,
        reference_data,
        "decision_1",
        force_tendential=force_tendential,
        strength=12.0,
    )
    if step1.empty:
        return {}

    first = str(step1.iloc[0]["opcion"])
    first_pct = float(step1.iloc[0]["porcentaje"])

    target1 = data[data["decision_1"] == first].copy()
    ref1 = reference_data[reference_data["decision_1"] == first].copy()
    step2, mode2, base2 = conditional_reading(
        target1,
        ref1,
        reference_data,
        "decision_2",
        force_tendential=force_tendential,
        strength=14.0,
    )
    step2 = step2[step2["opcion"] != first].reset_index(drop=True)
    if step2.empty:
        return {
            "first": first, "first_pct": first_pct, "first_base": base1, "first_mode": mode1,
            "second": "—", "second_pct": 0.0, "second_base": 0, "second_mode": "",
            "third": "—", "third_pct": 0.0, "third_base": 0, "third_mode": "",
        }

    second = str(step2.iloc[0]["opcion"])
    second_pct = float(step2.iloc[0]["porcentaje"])

    target12 = target1[target1["decision_2"] == second].copy()
    ref12 = ref1[ref1["decision_2"] == second].copy()
    broader_d3_ref = ref1 if len(ref1) else reference_data
    step3, mode3, base3 = conditional_reading(
        target12,
        ref12,
        broader_d3_ref,
        "decision_3",
        force_tendential=force_tendential,
        strength=12.0,
    )
    step3 = step3[~step3["opcion"].isin([first, second])].reset_index(drop=True)

    third = str(step3.iloc[0]["opcion"]) if len(step3) else "—"
    third_pct = float(step3.iloc[0]["porcentaje"]) if len(step3) else 0.0

    return {
        "first": first,
        "first_pct": first_pct,
        "first_base": base1,
        "first_mode": mode1,
        "second": second,
        "second_pct": second_pct,
        "second_base": base2,
        "second_mode": mode2,
        "third": third,
        "third_pct": third_pct,
        "third_base": base3,
        "third_mode": mode3,
    }


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


def short_tree_label(label: str) -> str:
    """Versión corta para nodos; el hover conserva el texto original."""
    mapping = {
        "Los beneficios del producto": "Beneficios del producto",
        "Que fuera fácil de aplicar": "Fácil de aplicar",
        "La necesidad que quería resolver": "Necesidad a resolver",
        "Mi experiencia previa con el producto": "Experiencia previa",
        "Que estuviera disponible": "Disponible",
    }
    return mapping.get(str(label), str(label))


def decision_tree_figure(
    data: pd.DataFrame,
    reference_data: pd.DataFrame,
    *,
    first_choice: str | None = None,
    force_tendential: bool = False,
    top_d1: int = 3,
    top_d2: int = 2,
    top_d3: int = 2,
    highlight_path: tuple[str | None, str | None, str | None] | None = None,
    detail_mode: str = "Medio",
) -> go.Figure:
    """Árbol ejecutivo con tarjetas y probabilidades condicionales por rama."""

    step1, mode1, base1 = conditional_reading(
        data,
        reference_data,
        reference_data,
        "decision_1",
        force_tendential=force_tendential,
        strength=12.0,
    )

    requested_first, requested_second, requested_third = (
        highlight_path if highlight_path else (None, None, None)
    )

    def _keep_selected(table: pd.DataFrame, selected: str | None, limit: int) -> pd.DataFrame:
        """Keep top-N but always include the manually selected option when available."""
        if table.empty or limit <= 0:
            return table.head(0).copy()
        shown = table.head(limit).copy()
        if selected and selected in table["opcion"].astype(str).tolist():
            if selected not in shown["opcion"].astype(str).tolist():
                selected_row = table[table["opcion"].astype(str) == str(selected)].head(1)
                if len(shown) >= limit:
                    shown = pd.concat([shown.iloc[:-1], selected_row], ignore_index=True)
                else:
                    shown = pd.concat([shown, selected_row], ignore_index=True)
        return shown.reset_index(drop=True)

    if first_choice and first_choice != "Todos":
        step1 = step1[step1["opcion"] == first_choice].copy()
    else:
        step1 = _keep_selected(step1, requested_first, top_d1)

    branches = []
    for d1_idx, (_, r1) in enumerate(step1.iterrows()):
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
        step2 = step2[step2["opcion"] != d1].copy()
        d2_limit = top_d2 if d1_idx == 0 else max(1, top_d2 - 1)
        selected_d2_for_branch = requested_second if d1 == requested_first else None
        step2 = _keep_selected(step2, selected_d2_for_branch, d2_limit)

        children2 = []
        for d2_idx, (_, r2) in enumerate(step2.iterrows()):
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
            step3 = step3[~step3["opcion"].isin([d1, d2])].copy()
            if top_d3 >= 3:
                # Vista Amplio: mostrar más alternativas de cierre.
                # La ruta principal conserva hasta 3 cierres y el resto hasta 2.
                d3_limit = top_d3 if d1_idx == 0 and d2_idx == 0 else 2
            else:
                # Simple/Medio: mantener el árbol compacto.
                d3_limit = top_d3 if d1_idx == 0 and d2_idx == 0 else 1
            selected_d3_for_branch = (
                requested_third
                if d1 == requested_first and d2 == requested_second
                else None
            )
            step3 = _keep_selected(step3, selected_d3_for_branch, d3_limit)

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

    # Posicionamiento vertical en unidades reales, no normalizadas.
    # Así cada nodo conserva una separación mínima en píxeles aunque cambie
    # el tamaño de la ventana, el nivel de detalle o la cantidad de ramas.
    cursor = 0.0
    # La densidad se adapta al nivel elegido por el cliente.
    if detail_mode == "Simple":
        leaf_gap = 0.92
        closure_gap = 1.15
        d2_group_gap = 0.16
        branch_gap = 0.42
        px_per_unit = 61
    elif detail_mode == "Amplio":
        leaf_gap = 1.04
        closure_gap = 1.42
        d2_group_gap = 0.30
        branch_gap = 0.58
        px_per_unit = 67
    else:
        leaf_gap = 0.98
        closure_gap = 1.28
        d2_group_gap = 0.22
        branch_gap = 0.50
        px_per_unit = 64
    for d1 in branches:
        d2_positions = []
        for d2 in d1["children"]:
            d3_positions = []
            if d2["children"]:
                for d3 in d2["children"]:
                    d3["y_raw"] = cursor
                    d3_positions.append(cursor)
                    cursor += closure_gap
                d2["y_raw"] = sum(d3_positions) / len(d3_positions)
                # Un poco de aire entre grupos de cierres pertenecientes a distintos D2.
                cursor += d2_group_gap
            else:
                d2["y_raw"] = cursor
                cursor += leaf_gap
            d2_positions.append(d2["y_raw"])
        if d2_positions:
            d1["y_raw"] = sum(d2_positions) / len(d2_positions)
        else:
            d1["y_raw"] = cursor
            cursor += leaf_gap
        cursor += branch_gap

    max_y = max(cursor - branch_gap, 1.0)

    for d1 in branches:
        d1["y"] = d1["y_raw"]
        for d2 in d1["children"]:
            d2["y"] = d2["y_raw"]
            for d3 in d2["children"]:
                d3["y"] = d3["y_raw"]

    root_y = sum(d["y"] for d in branches) / len(branches) if branches else max_y / 2

    # La ruta destacada puede venir de la exploración del usuario.
    if highlight_path:
        highlight_first, highlight_second, highlight_third = highlight_path
    else:
        highlight_first = branches[0]["label"] if branches else None
        highlight_second = (
            branches[0]["children"][0]["label"]
            if branches and branches[0]["children"] else None
        )
        highlight_third = (
            branches[0]["children"][0]["children"][0]["label"]
            if branches and branches[0]["children"] and branches[0]["children"][0]["children"]
            else None
        )

    fig = go.Figure()

    x_root, x_d1, x_d2, x_d3 = 0.20, 1.25, 2.55, 3.90
    main_blue = "#2F80ED"
    main_fill = "#F3F8FF"
    main_border = "#2F80ED"
    other_line = "rgba(151,174,197,0.62)"
    other_border = "#C9D7E4"
    other_fill = "#FBFCFE"
    text_color = "#163B60"

    def add_edge(x0, y0, x1, y1, pct, *, highlight=False):
        dx = x1 - x0
        c1x, c1y = x0 + dx * 0.34, y0
        c2x, c2y = x1 - dx * 0.34, y1
        ts = [i / 24 for i in range(25)]
        xs = [
            ((1-t)**3)*x0 + 3*((1-t)**2)*t*c1x + 3*(1-t)*(t**2)*c2x + (t**3)*x1
            for t in ts
        ]
        ys = [
            ((1-t)**3)*y0 + 3*((1-t)**2)*t*c1y + 3*(1-t)*(t**2)*c2y + (t**3)*y1
            for t in ts
        ]
        width = (4.0 if highlight else 1.55) + min(1.1, max(0.0, pct) / 55.0)
        fig.add_trace(go.Scatter(
            x=xs,
            y=ys,
            mode="lines",
            line=dict(
                width=width,
                color=main_blue if highlight else other_line,
                shape="linear",
            ),
            hoverinfo="skip",
            showlegend=False,
        ))

    def add_card(x, y, label, pct, base, mode, *, highlight=False, root=False):
        if root:
            fig.add_annotation(
                x=x, y=y,
                text="<b>Compra</b><br><span style='font-size:12px'>100%</span>",
                showarrow=False,
                xanchor="center",
                yanchor="middle",
                align="center",
                bgcolor="#0E3A63",
                bordercolor="#0E3A63",
                borderwidth=1,
                borderpad=12,
                font=dict(size=13.5, color="white"),
            )
            return

        full_label = str(label)
        display_label = short_tree_label(full_label)
        wrapped = _wrap_tree_label(display_label, width=19)

        # Tarjeta principal: el texto nunca compite visualmente con el porcentaje.
        fig.add_annotation(
            x=x - 0.035,
            y=y,
            text=f"<b>{wrapped}</b>",
            showarrow=False,
            xanchor="center",
            yanchor="middle",
            align="left",
            bgcolor=main_fill if highlight else other_fill,
            bordercolor=main_border if highlight else other_border,
            borderwidth=1.6 if highlight else 1,
            borderpad=8,
            font=dict(size=12.0, color=text_color),
            width=205,
            height=44,
        )

        # Porcentaje fijo: siempre visible y alineado a la derecha del nodo.
        fig.add_annotation(
            x=x + 0.205,
            y=y,
            text=f"<b>{pct:.1f}%</b>",
            showarrow=False,
            xanchor="center",
            yanchor="middle",
            align="center",
            bgcolor=main_blue if highlight else "#EAF2FA",
            bordercolor=main_blue if highlight else "#D1DFEC",
            borderwidth=1,
            borderpad=5,
            font=dict(size=13.8, color="white" if highlight else "#173A5E"),
        )

        # Zona invisible de hover sobre el nodo completo.
        fig.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode="markers",
            marker=dict(size=58, color="rgba(0,0,0,0)"),
            customdata=[[full_label, pct, base, mode]],
            hovertemplate=(
                "<b>%{customdata[0]}</b>"
                "<br>%{customdata[1]:.1f}% dentro de esta rama"
                "<br>Base de la rama: %{customdata[2]}"
                "<br>Lectura: %{customdata[3]}<extra></extra>"
            ),
            showlegend=False,
        ))

    add_card(x_root, root_y, "Compra", 100.0, len(data), "Observada", root=True)

    for d1 in branches:
        h1 = d1["label"] == highlight_first
        add_edge(x_root + 0.12, root_y, x_d1 - 0.22, d1["y"], d1["pct"], highlight=h1)
        add_card(
            x_d1, d1["y"], d1["label"], d1["pct"], d1["base"], d1["mode"],
            highlight=h1,
        )

        for d2 in d1["children"]:
            h2 = h1 and d2["label"] == highlight_second
            add_edge(x_d1 + 0.22, d1["y"], x_d2 - 0.22, d2["y"], d2["pct"], highlight=h2)
            add_card(
                x_d2, d2["y"], d2["label"], d2["pct"], d2["base"], d2["mode"],
                highlight=h2,
            )

            for d3 in d2["children"]:
                h3 = h2 and d3["label"] == highlight_third
                add_edge(x_d2 + 0.22, d2["y"], x_d3 - 0.22, d3["y"], d3["pct"], highlight=h3)
                add_card(
                    x_d3, d3["y"], d3["label"], d3["pct"], d3["base"], d3["mode"],
                    highlight=h3,
                )

    # Leyenda de lectura.
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines",
        line=dict(color=main_blue, width=5),
        name="Ruta principal",
        showlegend=True,
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines",
        line=dict(color=other_line, width=4),
        name="Otras rutas",
        showlegend=True,
    ))

    # Alto dinámico: Simple compacto, Amplio abre sólo lo necesario.
    vertical_span = max_y + 0.95
    min_height = 500 if detail_mode == "Simple" else 540 if detail_mode == "Medio" else 590
    max_height = 1150 if detail_mode == "Simple" else 1450 if detail_mode == "Medio" else 1750
    height = int(max(min_height, min(max_height, 150 + vertical_span * px_per_unit)))

    fig.update_layout(
        height=height,
        margin=dict(l=24, r=44, t=30, b=26),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(range=[-0.08, 4.28], visible=False, fixedrange=True),
        # Los encabezados viven fuera del gráfico; aquí sólo queda el árbol.
        yaxis=dict(range=[max_y + 0.42, -0.42], visible=False, fixedrange=True),
        hovermode="closest",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.075,
            xanchor="right",
            x=1.0,
            bgcolor="rgba(255,255,255,0)",
            font=dict(size=11, color="#6B7E93"),
        ),
    )
    return fig

def product_language(filters: dict) -> dict:
    """Client-facing terminology adapts to the selected product."""
    selected = filters.get("producto", []) or []
    if not isinstance(selected, list):
        selected = [selected]
    if len(selected) != 1:
        return {
            "concept": "tono o color",
            "short": "tono",
            "missing": "Tono/color no disponible",
            "switch_label": "Cambia de marca para conservar el tono o color que busca",
        }

    product = str(selected[0]).lower()
    if "shampoo" in product or "acondicionador" in product or "matizador" in product:
        return {
            "concept": "matiz o resultado de color",
            "short": "matiz/color",
            "missing": "Matiz/color no disponible",
            "switch_label": "Cambia de marca para conservar el matiz o resultado de color que busca",
        }
    if "decolorante" in product or "aclarante" in product:
        return {
            "concept": "resultado de aclaración",
            "short": "aclaración",
            "missing": "Resultado de aclaración no disponible",
            "switch_label": "Cambia de marca para conservar el resultado de aclaración que busca",
        }
    return {
        "concept": "tono o color",
        "short": "tono",
        "missing": "Tono/color no disponible",
        "switch_label": "Cambia de marca para conservar el tono o color que busca",
    }


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
    language: dict,
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

    concept = language["concept"]
    if tone >= 50:
        tone_phrase = f"el {concept} también domina con fuerza sobre la lealtad a marca ({tone:.1f}%)"
    elif tone >= 30:
        tone_phrase = f"el {concept} también puede provocar cambio de marca ({tone:.1f}%)"
    else:
        tone_phrase = f"el {concept} provoca menor cambio de marca ({tone:.1f}%)"

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
    language: dict,
) -> dict:
    """Cache by a stable filter key; deterministic across repeated selections."""
    key = _filter_signature(filters, reading_mode, n)
    cache = st.session_state.setdefault("insight_cache", {})
    if key not in cache:
        cache[key] = build_dynamic_insights(alcance, md, k, language)
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


def substitution_panel_html(k: dict, insight: str, language: dict) -> str:
    rows = [
        ("swap", "#D84B65", "#FDECEF", float(k["cambia_marca_si_falta_marca"]), "Cambia de marca si no encuentra su marca"),
        ("hair", "#E7862E", "#FFF2E6", float(k["cambia_marca_para_conservar_tono"]), language["switch_label"]),
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

# Validación explícita del formato seguro. También fuerza al despliegue a usar
# el runtime de cifrado actualizado que soporta paquetes multi-clave v2.
if not package_bytes.startswith(MAGIC) or len(package_bytes) <= len(MAGIC):
    st.error("El archivo no corresponde al formato seguro del estudio.")
    st.stop()

package_version = package_bytes[len(MAGIC)]
if package_version not in {VERSION, VERSION_MULTI}:
    st.error("El archivo utiliza una versión de seguridad no soportada por esta aplicación.")
    st.stop()

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

FILTER_WIDGET_KEYS = {col: f"filter_{col}" for col in FILTER_COLUMNS}

with st.sidebar:
    st.markdown(
        '''
        <div class="sidebar-hero">
          <div class="sidebar-kicker">PERSONALIZA LA LECTURA</div>
          <div class="sidebar-title-row">
            <div class="sidebar-icon">
              <svg width="23" height="23" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 5h16M7 12h10M10 19h4" fill="none" stroke="white" stroke-width="1.9" stroke-linecap="round"/>
                <circle cx="8" cy="5" r="2" fill="#7CC4F2"/>
                <circle cx="15" cy="12" r="2" fill="#A6D7F6"/>
                <circle cx="12" cy="19" r="2" fill="#D1EBFB"/>
              </svg>
            </div>
            <div class="sidebar-title">Filtros</div>
          </div>
          <div class="sidebar-copy">Define los cortes que quieres analizar y el dashboard se actualizará automáticamente.</div>
        </div>
        <div class="sidebar-status-card">
          <span class="sidebar-status-dot"></span>
          <div>
            <div class="sidebar-status-main">Estudio cargado</div>
            <div class="sidebar-status-sub">Listo para explorar</div>
          </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    action_cols = st.columns(2)
    with action_cols[0]:
        clear_filters = st.button("Limpiar", use_container_width=True, key="clear_filters_btn")
    with action_cols[1]:
        close_study = st.button("Cerrar", use_container_width=True, key="close_study_btn")

    if clear_filters:
        for widget_key in FILTER_WIDGET_KEYS.values():
            st.session_state[widget_key] = []
        st.rerun()

    if close_study:
        clear_loaded_data()
        st.rerun()

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="filter-section-label">Compra</div>', unsafe_allow_html=True)

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

for col in ["producto", "marca", "cadena"]:
    opts = options_for(df, col)
    filters[col] = st.sidebar.multiselect(
        filter_labels[col],
        opts,
        default=[],
        key=FILTER_WIDGET_KEYS[col],
        placeholder="Selecciona una o más opciones",
    )

st.sidebar.markdown('<div class="filter-section-label">Perfil</div>', unsafe_allow_html=True)

for col in ["edad_rango", "area_nielsen", "nse", "sexo"]:
    opts = options_for(df, col)
    filters[col] = st.sidebar.multiselect(
        filter_labels[col],
        opts,
        default=[],
        key=FILTER_WIDGET_KEYS[col],
        placeholder="Selecciona una o más opciones",
    )

filtered = apply_filters(df, filters)
n = len(filtered)
quality, quality_note = base_quality(n)
active_filter_count = sum(1 for values in filters.values() if values)
st.sidebar.markdown(
    f'''
    <div class="filter-summary-card">
      <div class="filter-summary-top">
        <span class="filter-summary-label">Base seleccionada</span>
        <span class="filter-summary-value">{n} entrevistas</span>
      </div>
      <div class="filter-summary-note">{active_filter_count} filtros activos</div>
    </div>
    ''',
    unsafe_allow_html=True,
)

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
    st.sidebar.markdown('<div class="filter-section-label">Tipo de lectura</div>', unsafe_allow_html=True)
    reading_mode = st.sidebar.radio(
        "Selecciona el modo",
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
    ("Resumen", "chart", "Resumen", "Vista ejecutiva"),
    ("Cómo se decide", "route", "Decisión de compra", "Cómo eligen"),
    ("Qué pesa más", "diamond", "Drivers clave", "Qué pesa más"),
    ("Qué pasa si falta...", "warning", "Riesgo de cambio", "Si algo falta"),
    ("Cómo ordenar el anaquel", "grid", "Anaquel", "Cómo facilitar la búsqueda"),
]

if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "Resumen"

st.markdown('<div class="nav-kicker">EXPLORA EL ESTUDIO</div>', unsafe_allow_html=True)
st.markdown('<div class="nav-title">¿Qué quieres explorar?</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="nav-subtitle">Elige una sección para profundizar en los principales hallazgos del estudio.</div>',
    unsafe_allow_html=True,
)

clicked_page = None
nav_cols = st.columns(5, gap="medium")

for idx, (page_name, icon_name, page_label, page_subtitle) in enumerate(NAV_ITEMS):
    is_active = st.session_state["nav_page"] == page_name
    tile_state = "active" if is_active else "idle"

    with nav_cols[idx]:
        with st.container(key=f"nav_tile_{idx}_{tile_state}", border=False):
            icon_color = "#FFFFFF" if is_active else "#2369A7"
            st.markdown(
                f'<div class="nav-icon-wrap">'
                f'<div class="nav-step-badge">{idx + 1}</div>'
                f'<div class="nav-icon-circle {"active" if is_active else ""}">'
                f'{icon_svg(icon_name, icon_color)}'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            if st.button(
                page_label,
                key=f"nav_card_{idx}",
                type="secondary",
                use_container_width=True,
            ):
                clicked_page = page_name

            st.markdown(
                f'<div class="nav-subline">{html.escape(page_subtitle)}</div>',
                unsafe_allow_html=True,
            )

            status = "ESTÁS AQUÍ" if is_active else ""
            status_class = "nav-status active" if is_active else "nav-status"
            st.markdown(
                f'<div class="{status_class}">{status}</div>',
                unsafe_allow_html=True,
            )

if clicked_page is not None and clicked_page != st.session_state["nav_page"]:
    st.session_state["nav_page"] = clicked_page
    st.rerun()

page = st.session_state["nav_page"]

# LOCKED SECTION — RESUMEN
# Aprobado por el usuario el 2026-10-01. No modificar sin solicitud explícita.
if page == "Resumen":
    st.markdown("### Resumen ejecutivo")
    st.caption("Una lectura rápida de qué consideran, qué genera valor y qué puede cambiar su elección.")
    k = tendential_kpis(filtered, reference) if is_tendential else executive_kpis(filtered)
    language = product_language(filters)

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

    if is_tendential:
        md = maxdiff_tendential(filtered, reference).head(5).copy()
        md["valor"] = md["tendencial"]
    else:
        md = maxdiff_compare(filtered, df).head(5).copy()
        md["valor"] = md["segmento"]

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

# LOCKED SECTION — DECISIÓN DE COMPRA
# Versión final aprobada por el usuario el 2026-10-01. No modificar sin solicitud explícita.
elif page == "Cómo se decide":
    base_reference = reference if is_tendential else filtered
    k_decision = tendential_kpis(filtered, reference) if is_tendential else executive_kpis(filtered)
    main_path = main_decision_path(
        filtered,
        base_reference,
        force_tendential=is_tendential,
    )

    main_first = main_path.get("first", "—")
    main_first_pct = float(main_path.get("first_pct", 0.0))
    main_second = main_path.get("second", "—")
    main_second_pct = float(main_path.get("second_pct", 0.0))
    main_third = main_path.get("third", "—")
    main_third_pct = float(main_path.get("third_pct", 0.0))

    # Distribución D1 disponible siempre: alimenta "Comenzar desde" y la exploración.
    if is_tendential:
        step1 = categorical_tendential(
            filtered,
            base_reference,
            "decision_1",
            strength=12.0,
            label_name="opcion",
        )[["opcion", "tendencial"]].rename(columns={"tendencial": "porcentaje"})
    else:
        counts1 = filtered["decision_1"].dropna().value_counts()
        step1 = pd.DataFrame({
            "opcion": counts1.index.astype(str),
            "porcentaje": counts1.values / counts1.sum() * 100,
        })

    first_options = step1["opcion"].tolist()

    st.markdown(
        f"""
        <div class="decision-header">
          <div class="decision-header-main">
            <div class="decision-header-icon">{icon_svg("route", "#1D6FB5")}</div>
            <div>
              <div class="decision-header-kicker">Decisión de compra</div>
              <div class="decision-header-title">Árbol de decisión de compra</div>
              <div class="decision-header-sub">Explora cómo avanza la elección y qué alternativas aparecen en cada paso.</div>
            </div>
          </div>
          <div class="decision-meta">
            <div class="decision-meta-card">
              <div class="decision-meta-label">Base analizada</div>
              <div class="decision-meta-value">{n} entrevistas</div>
            </div>
            <div class="decision-meta-card">
              <div class="decision-meta-label">La secuencia describe bien la decisión</div>
              <div class="decision-meta-value">{k_decision["validacion_arbol"]:.1f}%</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="decision_controls", border=True):
        c1, c2, c3 = st.columns([1.0, 1.0, 1.20])
        with c1:
            explore_mode = st.segmented_control(
                "Vista",
                options=["Vista general", "Explorar una ruta"],
                default="Vista general",
                key="decision_explore_mode",
            )
        with c2:
            detail = st.segmented_control(
                "Nivel de detalle",
                options=["Simple", "Medio", "Amplio"],
                default="Medio",
                key="decision_detail",
            )
        with c3:
            start_options = ["Todos"] + first_options
            start_from = st.selectbox(
                "Comenzar desde",
                start_options,
                index=0,
                key="decision_start_from",
                help="Todos conserva el árbol completo. Si eliges un criterio, el árbol comienza desde ese primer paso.",
            )

    if detail == "Simple":
        top_d1, top_d2, top_d3 = 2, 2, 1
    elif detail == "Amplio":
        top_d1, top_d2, top_d3 = 5, 3, 3
    else:
        top_d1, top_d2, top_d3 = 3, 2, 2

    # La ruta activa parte de la selección del cliente; si elige Todos, parte de la ruta principal.
    selected_first = main_first if start_from == "Todos" else start_from
    first_row = step1[step1["opcion"] == selected_first]
    selected_first_pct = float(first_row.iloc[0]["porcentaje"]) if len(first_row) else main_first_pct

    target1 = filtered[filtered["decision_1"] == selected_first].copy()
    ref1 = base_reference[base_reference["decision_1"] == selected_first].copy()
    step2, _, _ = conditional_reading(
        target1,
        ref1,
        base_reference,
        "decision_2",
        force_tendential=is_tendential,
        strength=14.0,
    )
    step2 = step2[step2["opcion"] != selected_first].reset_index(drop=True)
    second_options = step2["opcion"].tolist()

    if selected_first == main_first and main_second in second_options:
        selected_second = main_second
    else:
        selected_second = second_options[0] if second_options else "—"
    second_row = step2[step2["opcion"] == selected_second]
    selected_second_pct = float(second_row.iloc[0]["porcentaje"]) if len(second_row) else 0.0

    target12 = target1[target1["decision_2"] == selected_second].copy() if selected_second != "—" else target1.iloc[0:0].copy()
    ref12 = ref1[ref1["decision_2"] == selected_second].copy() if selected_second != "—" else ref1.iloc[0:0].copy()
    broader = ref1 if len(ref1) else base_reference
    step3, _, _ = conditional_reading(
        target12,
        ref12,
        broader,
        "decision_3",
        force_tendential=is_tendential,
        strength=12.0,
    )
    step3 = step3[~step3["opcion"].isin([selected_first, selected_second])].reset_index(drop=True)
    third_options = step3["opcion"].tolist()

    if selected_first == main_first and selected_second == main_second and main_third in third_options:
        selected_third = main_third
    else:
        selected_third = third_options[0] if third_options else "—"
    third_row = step3[step3["opcion"] == selected_third]
    selected_third_pct = float(third_row.iloc[0]["porcentaje"]) if len(third_row) else 0.0

    focus_branch = False

    if explore_mode == "Explorar una ruta":
        r1, r2 = st.columns([1.0, 1.0])

        with r1:
            if second_options:
                second_default = second_options.index(selected_second) if selected_second in second_options else 0
                selected_second = st.selectbox(
                    "Después",
                    second_options,
                    index=second_default,
                    key="decision_dynamic_second",
                )
                second_row = step2[step2["opcion"] == selected_second]
                selected_second_pct = float(second_row.iloc[0]["porcentaje"]) if len(second_row) else 0.0

        # Recalcular D3 al cambiar el segundo paso.
        target12 = target1[target1["decision_2"] == selected_second].copy() if selected_second != "—" else target1.iloc[0:0].copy()
        ref12 = ref1[ref1["decision_2"] == selected_second].copy() if selected_second != "—" else ref1.iloc[0:0].copy()
        step3, _, _ = conditional_reading(
            target12,
            ref12,
            broader,
            "decision_3",
            force_tendential=is_tendential,
            strength=12.0,
        )
        step3 = step3[~step3["opcion"].isin([selected_first, selected_second])].reset_index(drop=True)
        third_options = step3["opcion"].tolist()

        with r2:
            if third_options:
                preferred_third = (
                    main_third
                    if selected_first == main_first and selected_second == main_second and main_third in third_options
                    else third_options[0]
                )
                third_default = third_options.index(preferred_third)
                selected_third = st.selectbox(
                    "Cierre",
                    third_options,
                    index=third_default,
                    key="decision_dynamic_third",
                )
                third_row = step3[step3["opcion"] == selected_third]
                selected_third_pct = float(third_row.iloc[0]["porcentaje"]) if len(third_row) else 0.0
            else:
                selected_third = "—"
                selected_third_pct = 0.0

    highlight_path = (selected_first, selected_second, selected_third)

    # "Comenzar desde" controla realmente el punto de arranque del árbol.
    # Todos = contexto completo; una opción específica = árbol enfocado desde ese D1.
    first_choice_for_tree = selected_first if start_from != "Todos" else None

    with st.container(key="decision_tree_panel", border=True):
        st.markdown(
            """
            <div class="tree-column-heads">
              <div class="tree-column-head">
                <div class="tree-column-title">Inicio</div>
                <div class="tree-column-sub">Todos</div>
              </div>
              <div class="tree-column-head">
                <div class="tree-column-title">Primero</div>
                <div class="tree-column-sub">¿Qué aparece primero?</div>
              </div>
              <div class="tree-column-head">
                <div class="tree-column-title">Después</div>
                <div class="tree-column-sub">¿Qué sigue?</div>
              </div>
              <div class="tree-column-head">
                <div class="tree-column-title">Cierre</div>
                <div class="tree-column-sub">¿Qué termina definiendo?</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tree_fig = decision_tree_figure(
            filtered,
            base_reference,
            first_choice=first_choice_for_tree,
            force_tendential=is_tendential,
            top_d1=top_d1,
            top_d2=top_d2,
            top_d3=top_d3,
            highlight_path=highlight_path,
            detail_mode=detail,
        )
        tree_fig.update_layout(
            title=None,
            margin=dict(l=12, r=22, t=30, b=18),
            paper_bgcolor="white",
            plot_bgcolor="white",
        )
        st.plotly_chart(tree_fig, use_container_width=True)

        if start_from != "Todos":
            start_phrase = f"Comenzando desde <b>{html.escape(selected_first)}</b> ({selected_first_pct:.1f}% del total), "
        else:
            start_phrase = f"Ruta principal: <b>{html.escape(selected_first)}</b> ({selected_first_pct:.1f}% del total), "

        if selected_second != "—" and selected_third != "—":
            dynamic_text = (
                start_phrase
                + f"<b>{html.escape(selected_second)}</b> concentra {selected_second_pct:.1f}% dentro de esa rama y "
                + f"<b>{html.escape(selected_third)}</b> alcanza {selected_third_pct:.1f}% en el cierre."
            )
        elif selected_second != "—":
            dynamic_text = (
                start_phrase
                + f"<b>{html.escape(selected_second)}</b> concentra {selected_second_pct:.1f}% dentro de esa rama."
            )
        else:
            dynamic_text = start_phrase.rstrip(", ") + "."

        st.markdown(
            f'<div class="decision-dynamic-insight">{dynamic_text}</div>',
            unsafe_allow_html=True,
        )

# LOCKED SECTION — DRIVERS CLAVE
# Versión final aprobada por el usuario el 2026-10-01. No modificar sin solicitud explícita.
elif page == "Qué pesa más":
    # ===== Drivers clave · MaxDiff =====
    if is_tendential:
        comp = maxdiff_tendential(filtered, reference).copy()
        comp["actual"] = comp["tendencial"]
        comp["benchmark"] = comp["referencia"]
        comp["delta_actual"] = comp["delta_vs_referencia"]
        benchmark_label = "Categoría"
        reading_label = "Lectura tendencial"
    else:
        comp = maxdiff_compare(filtered, df).copy()
        comp["actual"] = comp["segmento"]
        comp["benchmark"] = comp["total"]
        comp["delta_actual"] = comp["delta"]
        benchmark_label = "Total"
        reading_label = "Selección actual"

    comp = comp.sort_values("actual", ascending=False).reset_index(drop=True)
    top3 = comp.head(3).copy()
    top1_name = str(top3.iloc[0]["driver"]) if len(top3) else "—"
    top1_value = float(top3.iloc[0]["actual"]) if len(top3) else 0.0
    top2_name = str(top3.iloc[1]["driver"]) if len(top3) > 1 else "—"
    top2_value = float(top3.iloc[1]["actual"]) if len(top3) > 1 else 0.0
    leader_gap = top1_value - top2_value if len(top3) > 1 else 0.0

    st.markdown(
        f"""
        <div class="drivers-header">
          <div class="drivers-header-main">
            <div class="drivers-header-icon">{icon_svg("diamond", "#1D6FB5")}</div>
            <div>
              <div class="drivers-header-kicker">Drivers clave</div>
              <div class="drivers-header-title">Qué genera mayor valor al elegir</div>
              <div class="drivers-header-sub">Ordena los factores por su peso relativo en la elección del producto.</div>
            </div>
          </div>
          <div class="drivers-meta">
            <div class="drivers-meta-label">Base analizada</div>
            <div class="drivers-meta-value">{n} entrevistas</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="driver_chart_panel", border=True):
        h1, h2 = st.columns([1.25, .75])
        with h1:
            st.markdown('<div class="driver-panel-title">Ranking de importancia</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="driver-panel-sub">Mayor score = mayor peso relativo en la decisión.</div>',
                unsafe_allow_html=True,
            )
        with h2:
            compare_mode = st.segmented_control(
                "Lectura",
                options=[reading_label, f"Comparar con {benchmark_label.lower()}"],
                default=f"Comparar con {benchmark_label.lower()}",
                key="driver_compare_mode",
            )

        if compare_mode == reading_label:
            plot = comp[["driver", "actual"]].rename(columns={"actual": "valor"}).copy()
            plot["serie"] = reading_label
        else:
            plot = comp[["driver", "actual", "benchmark"]].melt(
                id_vars=["driver"],
                value_vars=["actual", "benchmark"],
                var_name="serie",
                value_name="valor",
            )
            plot["serie"] = plot["serie"].map({
                "actual": reading_label,
                "benchmark": benchmark_label,
            })

        plot["etiqueta"] = plot["valor"].map(lambda x: f"{x:.1f}")
        order = comp["driver"].tolist()

        fig = px.bar(
            plot,
            x="valor",
            y="driver",
            color="serie",
            barmode="group",
            orientation="h",
            text="etiqueta",
            labels={"valor": "Score de importancia", "driver": "", "serie": ""},
        )
        fig.update_traces(textposition="outside", cliponaxis=False)

        # En comparación, destacar directamente en el gráfico las mayores brechas.
        # Se marcan máximo 3 para mantener una lectura limpia.
        if compare_mode != reading_label:
            gap_view = comp.copy()
            gap_view["abs_delta"] = gap_view["delta_actual"].abs()
            gap_view = gap_view[gap_view["abs_delta"] >= 0.5].nlargest(3, "abs_delta")

            if len(gap_view):
                max_score = float(max(comp["actual"].max(), comp["benchmark"].max()))
                gap_x = max_score + max(0.8, max_score * 0.07)

                for _, gap_row in gap_view.iterrows():
                    delta = float(gap_row["delta_actual"])
                    is_up = delta > 0
                    fig.add_annotation(
                        x=gap_x,
                        y=str(gap_row["driver"]),
                        text=f"<b>{'▲' if is_up else '▼'} {delta:+.1f}</b>",
                        showarrow=False,
                        xanchor="left",
                        yanchor="middle",
                        bgcolor="#EAF7F0" if is_up else "#FFF1F2",
                        bordercolor="#B9DFC9" if is_up else "#F0C6CC",
                        borderwidth=1,
                        borderpad=4,
                        font=dict(
                            size=11,
                            color="#237A4B" if is_up else "#A53D4A",
                        ),
                    )

                fig.add_annotation(
                    x=1,
                    y=1.075,
                    xref="paper",
                    yref="paper",
                    text="<b>▲ Sobreíndice</b> &nbsp;&nbsp; <b>▼ Bajo índice</b>",
                    showarrow=False,
                    xanchor="right",
                    font=dict(size=10, color="#718096"),
                )

        x_max = float(max(comp["actual"].max(), comp["benchmark"].max()))
        if compare_mode != reading_label and (comp["delta_actual"].abs() >= 0.5).any():
            x_max = x_max + max(2.2, x_max * 0.18)
        else:
            x_max = x_max + max(1.0, x_max * 0.08)

        fig.update_layout(
            yaxis=dict(
                categoryorder="array",
                categoryarray=list(reversed(order)),
            ),
            xaxis=dict(range=[0, x_max]),
            legend_title_text="",
            margin=dict(l=10, r=100, t=32, b=28),
            height=max(470, 72 + len(comp) * 42),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        fig.update_xaxes(showgrid=True, gridcolor="#E8EDF3", zeroline=False)
        st.plotly_chart(fig, use_container_width=True)

        if compare_mode != reading_label:
            relevant_gaps = comp[comp["delta_actual"].abs() >= 0.5]
            if len(relevant_gaps):
                st.caption(
                    "Las etiquetas ▲/▼ señalan las 3 mayores diferencias frente al "
                    f"{benchmark_label.lower()}. El valor indica la brecha en puntos de score."
                )
            else:
                st.caption(
                    f"No hay brechas de al menos 0.5 puntos frente al {benchmark_label.lower()} en la selección actual."
                )

    if len(comp):
        biggest_up = comp.sort_values("delta_actual", ascending=False).iloc[0]
        biggest_down = comp.sort_values("delta_actual", ascending=True).iloc[0]
        insight_parts = [
            f"<b>{html.escape(top1_name)}</b> lidera con un score de <b>{top1_value:.1f}</b>."
        ]
        if len(top3) > 1:
            if leader_gap >= 3:
                insight_parts.append(
                    f"La ventaja frente a <b>{html.escape(top2_name)}</b> es marcada ({leader_gap:.1f} puntos)."
                )
            else:
                insight_parts.append(
                    f"<b>{html.escape(top2_name)}</b> se mantiene cerca ({leader_gap:.1f} puntos de diferencia)."
                )

        if abs(float(biggest_up["delta_actual"])) >= 0.5:
            insight_parts.append(
                f"El mayor sobreíndice frente a {benchmark_label.lower()} está en "
                f"<b>{html.escape(str(biggest_up['driver']))}</b> ({float(biggest_up['delta_actual']):+.1f})."
            )

        with st.container(key="driver_insight_panel", border=True):
            st.markdown('<div class="driver-panel-title">Lectura clave</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="driver-insight">{" ".join(insight_parts)}</div>',
                unsafe_allow_html=True,
            )

    with st.expander("Ver detalle numérico"):
        if is_tendential:
            table = comp[["driver", "observado", "actual", "benchmark", "delta_actual"]].rename(
                columns={
                    "driver": "Factor",
                    "observado": "Dato observado",
                    "actual": "Lectura tendencial",
                    "benchmark": benchmark_label,
                    "delta_actual": f"Diferencia vs {benchmark_label.lower()}",
                }
            )
        else:
            table = comp[["driver", "actual", "benchmark", "delta_actual"]].rename(
                columns={
                    "driver": "Factor",
                    "actual": reading_label,
                    "benchmark": benchmark_label,
                    "delta_actual": "Diferencia",
                }
            )
        st.dataframe(
            table.style.format({col: "{:.1f}" for col in table.columns if col != "Factor"}),
            use_container_width=True,
            hide_index=True,
        )

    st.caption("Los scores MaxDiff expresan importancia relativa: se usan para ordenar y comparar factores, no como porcentajes de mención.")

# LOCKED SECTION — RIESGO DE CAMBIO
# Versión final aprobada por el usuario el 2026-10-01. No modificar sin solicitud explícita.
elif page == "Qué pasa si falta...":
    # ===== Riesgo de cambio =====
    language = product_language(filters)

    if is_tendential:
        k = tendential_kpis(filtered, reference)
    else:
        k = substitution_kpis(filtered)

    brand_risk = float(k["cambia_marca_si_falta_marca"])
    tone_risk = float(k["cambia_marca_para_conservar_tono"])
    promo_resilience = float(k["compra_sin_promocion"])

    st.markdown(
        f"""
        <div class="risk-header">
          <div class="risk-header-main">
            <div class="risk-header-icon">{icon_svg("warning", "#C7435B")}</div>
            <div>
              <div class="risk-header-kicker">Riesgo de cambio</div>
              <div class="risk-header-title">Qué pasa si no encuentra lo que quiere</div>
              <div class="risk-header-sub">Mide qué tan fácil es perder la elección cuando falta la marca, el {html.escape(language["concept"])} o la promoción.</div>
            </div>
          </div>
          <div class="risk-meta">
            <div class="risk-meta-label">Base analizada</div>
            <div class="risk-meta-value">{n} entrevistas</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="risk-kpi-grid">'
        '<div class="risk-kpi-card">'
        '<div><div class="risk-kpi-top">'
        f'<div class="risk-kpi-icon" style="background:#FFF1F3">{icon_svg("brand_missing", "#C7435B")}</div>'
        '<div class="risk-kpi-label">Si falta la marca</div></div>'
        f'<div class="risk-kpi-value">{brand_risk:.1f}%</div>'
        '<div class="risk-kpi-note">cambiaría a otra marca en lugar de conservar la marca buscada.</div></div>'
        '</div>'
        '<div class="risk-kpi-card">'
        '<div><div class="risk-kpi-top">'
        f'<div class="risk-kpi-icon" style="background:#FFF6E9">{icon_svg("tone_missing", "#C77A19")}</div>'
        f'<div class="risk-kpi-label">Si falta su {html.escape(language["short"])}</div></div>'
        f'<div class="risk-kpi-value">{tone_risk:.1f}%</div>'
        f'<div class="risk-kpi-note">cambiaría de marca para conservar el {html.escape(language["concept"])} que busca.</div></div>'
        '</div>'
        '<div class="risk-kpi-card">'
        '<div><div class="risk-kpi-top">'
        f'<div class="risk-kpi-icon" style="background:#EAF7F0">{icon_svg("promo_missing", "#237A4B")}</div>'
        '<div class="risk-kpi-label">Sin promoción</div></div>'
        f'<div class="risk-kpi-value">{promo_resilience:.1f}%</div>'
        '<div class="risk-kpi-note">compraría el producto de todos modos; indica resiliencia frente a la promoción.</div></div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.container(key="risk_sim_panel", border=True):
        st.markdown('<div class="risk-panel-title">Explora una situación de riesgo</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="risk-panel-sub">Selecciona el escenario para ver cómo reaccionan los compradores ante la falta de una condición esperada.</div>',
            unsafe_allow_html=True,
        )

        scenario_display = st.segmented_control(
            "Escenario",
            options=["Marca no disponible", language["missing"], "Sin promoción"],
            default="Marca no disponible",
            key="risk_scenario",
        )

        scenario = (
            "Tono/color no disponible"
            if scenario_display == language["missing"]
            else scenario_display
        )

        if is_tendential:
            t = substitution_tendential(filtered, reference, scenario).copy()
            t["porcentaje"] = t["tendencial"]
        else:
            t = scenario_counts(filtered, scenario, 1000).copy()
            t["porcentaje"] = t["pct"]

        t = t.sort_values("porcentaje", ascending=False).reset_index(drop=True)
        t["etiqueta"] = t["porcentaje"].map(lambda x: f"{float(x):.1f}%")

        fig = px.bar(
            t.sort_values("porcentaje"),
            x="porcentaje",
            y="respuesta",
            orientation="h",
            text="etiqueta",
            labels={"porcentaje": "Porcentaje", "respuesta": ""},
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        max_pct = float(t["porcentaje"].max()) if len(t) else 0.0
        fig.update_layout(
            height=max(430, 110 + len(t) * 46),
            margin=dict(l=10, r=90, t=18, b=28),
            plot_bgcolor="white",
            paper_bgcolor="white",
            yaxis=dict(categoryorder="total ascending"),
            xaxis=dict(range=[0, max(100, max_pct * 1.22)]),
        )
        fig.update_xaxes(showgrid=True, gridcolor="#E8EDF3", zeroline=False, ticksuffix="%")
        st.plotly_chart(fig, use_container_width=True)

    st.caption("Los porcentajes describen la reacción declarada ante cada escenario; no representan una proyección de ventas.")

elif page == "Cómo ordenar el anaquel":
    # ===== Anaquel · recomendación estadística =====
    shelf_reference = reference if is_tendential else df

    if n < 30:
        shrink_strength = 24.0
    elif n < 60:
        shrink_strength = 16.0
    elif n < 100:
        shrink_strength = 8.0
    else:
        shrink_strength = 0.0

    # Bootstrap y semilla están fijados dentro del motor para que el mismo corte
    # siempre produzca exactamente los mismos resultados.
    stat_rank = shelf_statistical_model(
        filtered,
        shelf_reference,
        shrink_strength=shrink_strength,
    )

    if is_tendential:
        easy, barriers = friction_tendential(filtered, reference)
        easy_value = float(easy["tendencial"])
        raw_priority = shelf_priority_tendential(filtered, reference).copy()
        raw_priority["valor_descriptivo"] = raw_priority["indice_tendencial"]
    else:
        easy_value, barriers = friction_summary(filtered)
        easy_value = float(easy_value)
        raw_priority = shelf_priority(filtered).copy()
        raw_priority["valor_descriptivo"] = raw_priority["indice_prioridad"]

    st.markdown(
        f"""
        <div class="shelf-header">
          <div class="shelf-header-main">
            <div class="shelf-header-icon">{icon_svg("grid", "#1D6FB5")}</div>
            <div>
              <div class="shelf-header-kicker">Anaquel</div>
              <div class="shelf-header-title">Cómo facilitar la compra en anaquel</div>
              <div class="shelf-header-sub">Traduce las preferencias de navegación en una jerarquía práctica para el anaquel.</div>
            </div>
          </div>
          <div class="shelf-meta">
            <div class="shelf-meta-label">Base analizada</div>
            <div class="shelf-meta-value">{n} entrevistas</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Resumen ejecutivo: mostrar sólo métricas fáciles de interpretar.
    executive_rank = (
        stat_rank.sort_values(
            ["prob_estimada", "posicion_media"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
        .copy()
    )
    with st.container(key="shelf_combo_panel", border=True):
        h1, h2 = st.columns([1.15, .85])
        with h1:
            st.markdown('<div class="shelf-panel-title">Orden recomendado</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="shelf-panel-sub">Tres niveles: guía principal, segundo filtro y apoyo complementario. <b>Los tres porcentajes usan la misma métrica: preferencia modelada con Plackett–Luce.</b></div>',
                unsafe_allow_html=True,
            )
        with h2:
            shelf_mode = st.segmented_control(
                "Modo",
                options=["Orden recomendado", "Probar organización"],
                default="Orden recomendado",
                key="shelf_mode",
            )

        all_options = executive_rank["organizacion"].tolist()
        recommended_primary = str(executive_rank.iloc[0]["organizacion"]) if len(executive_rank) else "—"

        if shelf_mode == "Orden recomendado":
            primary = recommended_primary
        else:
            primary = st.selectbox(
                "Organizar primero por",
                all_options,
                index=all_options.index(recommended_primary) if recommended_primary in all_options else 0,
                key="shelf_primary",
            )

        conditional_strength = 12.0 if n < 60 else 8.0 if n < 100 else 4.0
        conditional = shelf_conditional_model(
            filtered,
            primary,
            shelf_reference,
            strength=conditional_strength,
        )

        cond_options = conditional["organizacion"].tolist()
        recommended_secondary = str(conditional.iloc[0]["organizacion"]) if len(conditional) else "—"

        if shelf_mode == "Orden recomendado":
            secondary = recommended_secondary
        else:
            secondary = st.selectbox(
                "Después apoyar con",
                cond_options,
                index=0,
                key="shelf_secondary",
            ) if cond_options else "—"

        remaining_rank = executive_rank[
            ~executive_rank["organizacion"].isin([primary, secondary])
        ].copy()
        recommended_tertiary = (
            str(remaining_rank.iloc[0]["organizacion"]) if len(remaining_rank) else "—"
        )

        if shelf_mode == "Orden recomendado":
            tertiary = recommended_tertiary
        else:
            tertiary_options = remaining_rank["organizacion"].tolist()
            tertiary = st.selectbox(
                "Como tercer apoyo",
                tertiary_options,
                index=0,
                key="shelf_tertiary",
            ) if tertiary_options else "—"

        selected_secondary_row = conditional[conditional["organizacion"] == secondary]
        secondary_prob = float(selected_secondary_row.iloc[0]["prob_condicional"]) if len(selected_secondary_row) else 0.0
        branch_n = int(selected_secondary_row.iloc[0]["n_rama"]) if len(selected_secondary_row) else 0

        selected_primary_row = executive_rank[executive_rank["organizacion"] == primary]
        primary_pref = float(selected_primary_row.iloc[0]["prob_estimada"]) if len(selected_primary_row) else 0.0

        selected_secondary_pl_row = executive_rank[executive_rank["organizacion"] == secondary]
        secondary_pref = float(selected_secondary_pl_row.iloc[0]["prob_estimada"]) if len(selected_secondary_pl_row) else 0.0

        selected_tertiary_row = executive_rank[executive_rank["organizacion"] == tertiary]
        tertiary_pref = float(selected_tertiary_row.iloc[0]["prob_estimada"]) if len(selected_tertiary_row) else 0.0

        def _shelf_blocks(label: str) -> list[str]:
            txt = str(label).lower()
            if "necesidad" in txt:
                return ["Cubrir canas", "Retocar raíz", "Cambiar look", "Mantener color"]
            if "tipo de producto" in txt:
                vals = (
                    filtered["producto"].dropna().astype(str).value_counts().head(4).index.tolist()
                    if "producto" in filtered.columns else []
                )
                return vals if vals else ["Tinte", "Retocador", "Matizador", "Decolorante"]
            if "tono" in txt or "color" in txt:
                return ["Rubio", "Castaño", "Negro", "Rojo / cobrizo"]
            if "marca" in txt:
                vals = (
                    filtered["marca"].dropna().astype(str).value_counts().head(4).index.tolist()
                    if "marca" in filtered.columns else []
                )
                return vals if vals else ["Marca 1", "Marca 2", "Marca 3", "Marca 4"]
            if "precio" in txt or "promoción" in txt or "promocion" in txt:
                return ["Precio visible", "Promoción", "Ahorro", "Comparación"]
            if "beneficio" in txt:
                return ["Cobertura", "Duración", "Menor daño", "Hidratación"]
            if "señal" in txt or "guía" in txt or "guia" in txt:
                return ["Guía rápida", "Código visual", "Señalización", "Ayuda"]
            if "identificar" in txt:
                return ["Necesidad visible", "Uso", "Beneficio clave", "Producto recomendado"]
            return ["Zona 1", "Zona 2", "Zona 3", "Zona 4"]

        primary_blocks = _shelf_blocks(primary)
        secondary_blocks = _shelf_blocks(secondary)
        tertiary_blocks = _shelf_blocks(tertiary)
        primary_chips = "".join(
            f'<span class="shelf-route-chip">{html.escape(str(item))}</span>'
            for item in primary_blocks[:4]
        )
        secondary_chips = "".join(
            f'<span class="shelf-route-chip">{html.escape(str(item))}</span>'
            for item in secondary_blocks[:4]
        )
        tertiary_chips = "".join(
            f'<span class="shelf-route-chip">{html.escape(str(item))}</span>'
            for item in tertiary_blocks[:4]
        )

        visual_html = (
            '<div class="shelf-route-grid">'
              '<div class="shelf-route-card">'
                '<div class="shelf-route-card-head">'
                  '<div class="shelf-route-step">1</div>'
                  '<div>'
                    '<div class="shelf-route-kicker">Guía principal</div>'
                    f'<div class="shelf-route-name">{html.escape(primary)}</div>'
                    '<div class="shelf-route-explain">Ayuda a ubicar primero el producto.</div>'
                  '</div>'
                '</div>'
                f'<div class="shelf-route-metric">{primary_pref:.1f}% </div>'
                '<div class="shelf-route-examples-label">Ejemplos</div>'
                f'<div class="shelf-route-chips">{primary_chips}</div>'
              '</div>'
              '<div class="shelf-route-arrow">→</div>'
              '<div class="shelf-route-card secondary">'
                '<div class="shelf-route-card-head">'
                  '<div class="shelf-route-step">2</div>'
                  '<div>'
                    '<div class="shelf-route-kicker">Segundo filtro</div>'
                    f'<div class="shelf-route-name">{html.escape(secondary)}</div>'
                    '<div class="shelf-route-explain">Afina la elección dentro del primer nivel.</div>'
                  '</div>'
                '</div>'
                f'<div class="shelf-route-metric">{secondary_pref:.1f}% </div>'
                '<div class="shelf-route-examples-label">Ejemplos</div>'
                f'<div class="shelf-route-chips">{secondary_chips}</div>'
              '</div>'
              '<div class="shelf-route-arrow">→</div>'
              '<div class="shelf-route-card tertiary">'
                '<div class="shelf-route-card-head">'
                  '<div class="shelf-route-step">3</div>'
                  '<div>'
                    '<div class="shelf-route-kicker">Apoyo complementario</div>'
                    f'<div class="shelf-route-name">{html.escape(tertiary)}</div>'
                    '<div class="shelf-route-explain">Refuerza la navegación como tercer nivel.</div>'
                  '</div>'
                '</div>'
                f'<div class="shelf-route-metric">{tertiary_pref:.1f}% </div>'
                '<div class="shelf-route-examples-label">Ejemplos</div>'
                f'<div class="shelf-route-chips">{tertiary_chips}</div>'
              '</div>'
            '</div>'
            '<div class="shelf-route-meaning" style="margin-top:14px">'
              '<div class="shelf-route-label">Lectura para el anaquel</div>'
              f'<div class="shelf-route-meaning-main">{html.escape(primary)} → {html.escape(secondary)} → {html.escape(tertiary)}</div>'
              '<div class="shelf-route-copy">Los tres porcentajes de arriba son comparables entre sí porque provienen del mismo modelo Plackett–Luce.</div>'
              f'<div class="shelf-route-note"><b>Dato adicional de la ruta:</b> entre quienes eligieron {html.escape(primary)} primero, {secondary_prob:.1f}% eligió después {html.escape(secondary)} (base {branch_n}).</div>'
            '</div>'
        )
        st.markdown(visual_html, unsafe_allow_html=True)

        if shelf_mode == "Probar organización":
            st.markdown(
                f'<div class="shelf-insight"><b>Jerarquía probada:</b> '
                f'<b>{html.escape(primary)}</b> → <b>{html.escape(secondary)}</b> → <b>{html.escape(tertiary)}</b>.</div>',
                unsafe_allow_html=True,
            )

    with st.container(key="shelf_rank_panel", border=True):
        st.markdown('<div class="shelf-panel-title">Preferencia modelada de organización</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="shelf-panel-sub"><b>Modelo Plackett–Luce:</b> combina la primera ayuda (A1) y la segunda ayuda (A2) para estimar el peso relativo de cada forma de organizar el anaquel.</div>',
            unsafe_allow_html=True,
        )

        ranked_plot = executive_rank.sort_values("prob_estimada", ascending=True).copy()
        top_org = str(executive_rank.iloc[0]["organizacion"]) if len(executive_rank) else ""
        bar_colors = [
            "#1D76BE" if str(org) == top_org else "#A9CFF0"
            for org in ranked_plot["organizacion"]
        ]

        fig = go.Figure(
            go.Bar(
                x=ranked_plot["prob_estimada"],
                y=ranked_plot["organizacion"],
                orientation="h",
                text=ranked_plot["prob_estimada"].map(lambda x: f"{float(x):.1f}%"),
                textposition="outside",
                marker=dict(color=bar_colors),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Preferencia Plackett–Luce: %{x:.1f}%<extra></extra>"
                ),
            )
        )
        max_pref = float(ranked_plot["prob_estimada"].max()) if len(ranked_plot) else 0.0
        fig.update_layout(
            height=max(430, 100 + len(ranked_plot) * 46),
            margin=dict(l=10, r=95, t=18, b=28),
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(range=[0, max(40, max_pref * 1.25)]),
            yaxis=dict(title=""),
        )
        fig.update_xaxes(
            showgrid=True,
            gridcolor="#E8EDF3",
            zeroline=False,
            title="Preferencia modelada (Plackett–Luce)",
            ticksuffix="%",
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Cómo se calcula"):
            st.markdown(
                "**Plackett–Luce** aprovecha el orden de respuesta de cada persona: "
                "**A1 = primera ayuda** y **A2 = segunda ayuda**. Con esas posiciones estima una "
                "**preferencia modelada** para cada forma de organizar el anaquel. "
                "Por eso, por ejemplo, 31.9% es una estimación del modelo y no el porcentaje directo de personas que la mencionó."
            )
            st.markdown(
                f"Después se repite el cálculo **{SHELF_BOOTSTRAP_REPS} veces** mediante bootstrap. "
                "Esto sirve para revisar si el orden cambia al volver a muestrear la misma base. "
                f"Si una alternativa lidera en {SHELF_BOOTSTRAP_REPS}/{SHELF_BOOTSTRAP_REPS} remuestras, significa que su **primer lugar es muy estable**; "
                "**no significa que 100% de los entrevistados la haya elegido**."
            )

            tech = stat_rank[[
                "organizacion",
                "prob_estimada",
                "ic_bajo",
                "ic_alto",
                "posicion_media",
                "estabilidad_top1",
            ]].copy()

            tech["IC 95%"] = tech.apply(
                lambda r: f'{float(r["ic_bajo"]):.1f}%–{float(r["ic_alto"]):.1f}%',
                axis=1,
            )
            tech["Lideró en remuestras"] = tech["estabilidad_top1"].map(
                lambda x: f"{int(round(float(x) / 100.0 * SHELF_BOOTSTRAP_REPS))}/{SHELF_BOOTSTRAP_REPS}"
            )
            tech = tech.rename(columns={
                "organizacion": "Organización",
                "prob_estimada": "Preferencia PL",
                "posicion_media": "Ranking medio",
            })[[
                "Organización",
                "Preferencia PL",
                "IC 95%",
                "Ranking medio",
                "Lideró en remuestras",
            ]]

            st.dataframe(
                tech.style.format({
                    "Preferencia PL": "{:.1f}%",
                    "Ranking medio": "{:.2f}",
                }),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "Lectura rápida: menor ranking medio = mejor posición. "
                "“Lideró en remuestras” mide estabilidad del primer lugar, no porcentaje de personas."
            )

    with st.container(key="shelf_friction_panel", border=True):
        st.markdown('<div class="shelf-panel-title">Fricción al encontrar el producto</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="shelf-panel-sub">Muestra qué tan fácil fue encontrarlo y cuál fue la principal barrera.</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="shelf-ease-box">
              <div class="shelf-ease-value">{easy_value:.1f}%</div>
              <div class="shelf-ease-copy">encontró el producto <b>fácil o muy fácil</b>.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if len(barriers):
            barriers = barriers.copy()
            if is_tendential:
                barriers["porcentaje"] = barriers["tendencial"]
            else:
                barriers["porcentaje"] = barriers["pct"]

            barriers = barriers.sort_values("porcentaje", ascending=False).reset_index(drop=True)
            barriers["etiqueta"] = barriers["porcentaje"].map(lambda x: f"{float(x):.1f}%")

            fig2 = px.bar(
                barriers.sort_values("porcentaje"),
                x="porcentaje",
                y="barrera",
                orientation="h",
                text="etiqueta",
                labels={"porcentaje": "Porcentaje", "barrera": ""},
            )
            fig2.update_traces(textposition="outside", cliponaxis=False)
            max_bar = float(barriers["porcentaje"].max()) if len(barriers) else 0.0
            fig2.update_layout(
                height=max(390, 95 + len(barriers) * 44),
                margin=dict(l=10, r=80, t=18, b=28),
                plot_bgcolor="white",
                paper_bgcolor="white",
                yaxis=dict(categoryorder="total ascending"),
                xaxis=dict(range=[0, max(100, max_bar * 1.20)]),
            )
            fig2.update_xaxes(showgrid=True, gridcolor="#E8EDF3", zeroline=False, ticksuffix="%")
            st.plotly_chart(fig2, use_container_width=True)


st.markdown(
    '''
    <div class="footer-credit">
      <div class="footer-credit-left">Wella · Decision Simulator</div>
      <div class="footer-credit-right">
        <div class="footer-credit-kicker">Desarrollado por</div>
        <div class="footer-credit-brand">Go-Ideas</div>
      </div>
    </div>
    ''',
    unsafe_allow_html=True,
)
