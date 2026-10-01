from __future__ import annotations
import json, sqlite3
from pathlib import Path
import pandas as pd
import numpy as np

FILTER_COLUMNS = ["producto", "marca", "cadena", "edad_rango", "area_nielsen", "nse", "sexo"]

# Anaquel statistical runtime: fixed for reproducibility in the client dashboard.
SHELF_BOOTSTRAP_SEED = 20261001
SHELF_BOOTSTRAP_REPS = 300
MD_LABELS = {
    "md_necesidad": "Resolver necesidad principal",
    "md_tipo_producto": "Tipo de producto buscado",
    "md_tono": "Tono/color deseado",
    "md_marca_conocida": "Marca conocida / de confianza",
    "md_precio": "Precio adecuado",
    "md_promocion": "Promoción",
    "md_cobertura_duracion": "Cobertura y duración del color",
    "md_menor_dano": "Menor daño / sin amoníaco",
    "md_hidratacion": "Hidratación / tratamiento",
    "md_facilidad": "Facilidad de aplicación",
    "md_confianza_marca": "Confianza en la marca",
}

BASE_RULES = [
    (200, "ROBUSTA"),
    (100, "ESTABLE"),
    (60, "DIRECCIONAL"),
    (30, "EXPLORATORIA"),
    (0, "NO REPORTAR %"),
]

class InvalidDatabase(Exception):
    pass


def load_database_connection(con: sqlite3.Connection) -> tuple[pd.DataFrame, dict]:
    """Load and validate the analytical contract from an already-open SQLite connection."""
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "respondents" not in tables or "metadata" not in tables:
        raise InvalidDatabase("La base no cumple el contrato del simulador: faltan respondents/metadata.")
    df = pd.read_sql_query("SELECT * FROM respondents", con)
    meta_df = pd.read_sql_query("SELECT key, value FROM metadata", con)
    meta = {}
    for _, row in meta_df.iterrows():
        v = row["value"]
        try:
            meta[row["key"]] = json.loads(v)
        except Exception:
            meta[row["key"]] = v
    validate_dataframe(df)
    return df, meta


def load_database_bytes(file_bytes: bytes) -> tuple[pd.DataFrame, dict]:
    """Backward-compatible loader for local tests; uses SQLite deserialize and never writes plaintext to disk."""
    if not file_bytes:
        raise InvalidDatabase("El archivo está vacío.")
    con = sqlite3.connect(":memory:")
    try:
        if not hasattr(con, "deserialize"):
            raise InvalidDatabase("Este runtime no soporta SQLite deserialize en memoria.")
        con.deserialize(file_bytes)
        return load_database_connection(con)
    finally:
        con.close()


def load_database_path(path: str | Path) -> tuple[pd.DataFrame, dict]:
    p = Path(path)
    return load_database_bytes(p.read_bytes())

def validate_dataframe(df: pd.DataFrame) -> None:
    required = {
        "respondent_id", "producto", "marca", "cadena", "edad_rango", "area_nielsen", "nse", "sexo",
        "decision_1", "decision_2", "decision_3", "decision_validacion",
        "anaquel_1", "anaquel_2", "sust_marca", "sust_tono", "sust_promocion",
        "facilidad_encontrar", "barrera_principal",
    } | set(MD_LABELS)
    missing = sorted(required - set(df.columns))
    if missing:
        raise InvalidDatabase("Faltan variables requeridas: " + ", ".join(missing))
    if df.empty:
        raise InvalidDatabase("La base no contiene casos.")


def base_quality(n: int) -> tuple[str, str]:
    for min_n, label in BASE_RULES:
        if n >= min_n:
            if label == "ROBUSTA": return label, "Lectura apta para comparaciones principales."
            if label == "ESTABLE": return label, "Lectura general estable; comparar con cautela."
            if label == "DIRECCIONAL": return label, "Usar como señal o tendencia."
            if label == "EXPLORATORIA": return label, "Contexto exploratorio; no usar como decisión aislada."
            return label, "Base insuficiente para presentar porcentajes individuales."
    return "NO REPORTAR %", "Base insuficiente."


def apply_filters(df: pd.DataFrame, filters: dict[str, list[str] | str | None]) -> pd.DataFrame:
    out = df
    for col, selected in filters.items():
        if col not in out.columns or selected in (None, "Todos", ["Todos"], []):
            continue
        vals = selected if isinstance(selected, list) else [selected]
        if "Todos" in vals:
            continue
        out = out[out[col].isin(vals)]
    return out.copy()


def options_for(df: pd.DataFrame, col: str) -> list[str]:
    if col not in df.columns: return []
    return sorted([str(x) for x in df[col].dropna().unique()], key=lambda x: x.lower())


def pct_table(s: pd.Series, label_name="Respuesta") -> pd.DataFrame:
    x=s.dropna()
    if len(x)==0:
        return pd.DataFrame(columns=[label_name,"n","pct"])
    counts=x.value_counts(dropna=True)
    return pd.DataFrame({label_name:counts.index.astype(str),"n":counts.values,"pct":counts.values/len(x)*100})


def decision_stage_summary(df: pd.DataFrame) -> pd.DataFrame:
    frames=[]
    for stage,col in [("Primero","decision_1"),("Después","decision_2"),("Cierre","decision_3")]:
        t=pct_table(df[col],"criterio")
        t.insert(0,"etapa",stage); frames.append(t)
    return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()


def top_routes(df: pd.DataFrame, top_n=10) -> pd.DataFrame:
    tmp=df[["decision_1","decision_2","decision_3"]].dropna()
    if tmp.empty: return pd.DataFrame(columns=["ruta","n","pct"])
    g=(tmp.groupby(["decision_1","decision_2","decision_3"],dropna=False).size().reset_index(name="n").sort_values("n",ascending=False))
    g["pct"]=g["n"]/len(tmp)*100
    g["ruta"]=g["decision_1"].astype(str)+" → "+g["decision_2"].astype(str)+" → "+g["decision_3"].astype(str)
    return g[["ruta","n","pct"]].head(top_n).reset_index(drop=True)


def tree_links(df: pd.DataFrame, first_choice: str | None=None, top_d2=6, top_d3=4) -> dict:
    """Return compact Sankey-ready nodes/links. If first_choice is set, condition on D1."""
    d=df[["decision_1","decision_2","decision_3"]].dropna()
    if first_choice and first_choice != "Todos":
        d=d[d["decision_1"]==first_choice]
    if d.empty: return {"labels":[],"source":[],"target":[],"value":[],"custom":[]}

    labels=["Compra"]
    source=[]; target=[]; value=[]; custom=[]
    node_idx={"ROOT":0}

    if first_choice and first_choice != "Todos":
        d1_values=[first_choice]
    else:
        d1_values=d["decision_1"].value_counts().head(5).index.tolist()
        d=d[d["decision_1"].isin(d1_values)]

    for d1 in d1_values:
        key1=f"D1|{d1}"; node_idx[key1]=len(labels); labels.append(f"1º {d1}")
        n1=int((d["decision_1"]==d1).sum())
        source.append(0); target.append(node_idx[key1]); value.append(n1); custom.append(f"n={n1}")
        subset1=d[d["decision_1"]==d1]
        d2vals=subset1["decision_2"].value_counts().head(top_d2).index.tolist()
        for d2 in d2vals:
            key2=f"D2|{d1}|{d2}"; node_idx[key2]=len(labels); labels.append(f"2º {d2}")
            subset2=subset1[subset1["decision_2"]==d2]
            n2=len(subset2)
            source.append(node_idx[key1]); target.append(node_idx[key2]); value.append(n2); custom.append(f"n={n2} | {n2/max(n1,1)*100:.1f}% dentro de {d1}")
            d3vals=subset2["decision_3"].value_counts().head(top_d3).index.tolist()
            for d3 in d3vals:
                key3=f"D3|{d1}|{d2}|{d3}"; node_idx[key3]=len(labels); labels.append(f"3º {d3}")
                n3=int((subset2["decision_3"]==d3).sum())
                source.append(node_idx[key2]); target.append(node_idx[key3]); value.append(n3); custom.append(f"n={n3} | {n3/max(n2,1)*100:.1f}% dentro de la rama")
    return {"labels":labels,"source":source,"target":target,"value":value,"custom":custom}


def maxdiff_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for col,label in MD_LABELS.items():
        s=pd.to_numeric(df[col],errors="coerce")
        rows.append({"driver":label,"score":float(s.mean()) if s.notna().any() else np.nan,"n":int(s.notna().sum())})
    return pd.DataFrame(rows).sort_values("score",ascending=False).reset_index(drop=True)


def maxdiff_compare(filtered: pd.DataFrame, total: pd.DataFrame) -> pd.DataFrame:
    a=maxdiff_summary(filtered).rename(columns={"score":"segmento","n":"n_segmento"})
    b=maxdiff_summary(total).rename(columns={"score":"total","n":"n_total"})
    m=a.merge(b,on="driver",how="outer")
    m["delta"]=m["segmento"]-m["total"]
    return m.sort_values("segmento",ascending=False).reset_index(drop=True)


def substitution_summary(df: pd.DataFrame, scenario: str) -> pd.DataFrame:
    col={"Marca no disponible":"sust_marca","Tono/color no disponible":"sust_tono","Sin promoción":"sust_promocion"}[scenario]
    return pct_table(df[col],"respuesta")


def substitution_kpis(df: pd.DataFrame) -> dict:
    n=max(len(df),1)
    def share(col, codes):
        s=pd.to_numeric(df[col],errors="coerce")
        return float(s.isin(codes).sum()/s.notna().sum()*100) if s.notna().sum() else np.nan
    return {
        "cambia_marca_si_falta_marca": share("sust_marca_code", [1,2,3,4]),
        "cambia_marca_para_conservar_tono": share("sust_tono_code", [2]),
        "compra_sin_promocion": share("sust_promocion_code", [1]),
    }


def scenario_counts(df: pd.DataFrame, scenario: str, simulated_n: int=100) -> pd.DataFrame:
    t=substitution_summary(df,scenario).copy()
    if t.empty: return t
    t["esperados"]=np.rint(t["pct"]*simulated_n/100).astype(int)
    # adjust rounding to exactly N
    diff=simulated_n-int(t["esperados"].sum())
    if diff and len(t):
        order=(t["pct"]*simulated_n/100 - np.floor(t["pct"]*simulated_n/100)).sort_values(ascending=False).index.tolist()
        step=1 if diff>0 else -1
        for idx in order[:abs(diff)]: t.loc[idx,"esperados"] += step
    return t


def _plackett_luce_weights(rankings: pd.DataFrame, options: list[str]) -> np.ndarray:
    """Fit Plackett-Luce worths for observed top-2 rankings (A1 -> A2).

    The likelihood is P(A1=i) * P(A2=j | A1=i). The MM updates below are
    dependency-free and deterministic, which keeps the dashboard lightweight.
    """
    k = len(options)
    if k == 0:
        return np.array([], dtype=float)
    if k == 1:
        return np.array([1.0], dtype=float)

    idx = {opt: i for i, opt in enumerate(options)}
    first_counts = np.zeros(k, dtype=float)
    selected_counts = np.zeros(k, dtype=float)

    valid = rankings[["anaquel_1", "anaquel_2"]].dropna()
    for _, row in valid.iterrows():
        a = str(row["anaquel_1"])
        b = str(row["anaquel_2"])
        if a not in idx or b not in idx or a == b:
            continue
        first_counts[idx[a]] += 1.0
        selected_counts[idx[a]] += 1.0
        selected_counts[idx[b]] += 1.0

    n = float(first_counts.sum())
    if n <= 0:
        return np.ones(k, dtype=float) / k

    worth = np.ones(k, dtype=float)
    eps = 1e-12

    for _ in range(500):
        total = float(worth.sum())
        denom = np.full(k, n / max(total, eps), dtype=float)

        # Stage 2: option k is available whenever it was not selected first.
        for first_i, count in enumerate(first_counts):
            if count <= 0:
                continue
            stage_total = max(total - worth[first_i], eps)
            contribution = count / stage_total
            for option_i in range(k):
                if option_i != first_i:
                    denom[option_i] += contribution

        new_worth = np.divide(
            selected_counts,
            np.maximum(denom, eps),
            out=np.full(k, eps, dtype=float),
            where=denom > 0,
        )
        new_worth = np.maximum(new_worth, eps)
        new_worth /= new_worth.mean()

        if np.max(np.abs(np.log(new_worth / worth))) < 1e-9:
            worth = new_worth
            break
        worth = new_worth

    worth /= worth.sum()
    return worth


def shelf_statistical_model(
    df: pd.DataFrame,
    reference: pd.DataFrame | None = None,
    *,
    shrink_strength: float = 0.0,
    bootstrap: int = SHELF_BOOTSTRAP_REPS,
    seed: int = SHELF_BOOTSTRAP_SEED,
) -> pd.DataFrame:
    """Statistical shelf ranking from A1/A2 using Plackett-Luce + bootstrap.

    Returns a model-based first-choice probability ("prob_estimada"), a 95%
    bootstrap interval, and the probability of being ranked #1 across bootstrap
    resamples ("estabilidad_top1").

    For small filtered bases, optional partial pooling blends the filtered
    estimate toward the reference distribution.
    """
    target = (
        df[["anaquel_1", "anaquel_2"]]
        .dropna()
        .astype(str)
        .sort_values(["anaquel_1", "anaquel_2"], kind="mergesort")
        .reset_index(drop=True)
    )
    ref = (
        reference[["anaquel_1", "anaquel_2"]]
        .dropna()
        .astype(str)
        .sort_values(["anaquel_1", "anaquel_2"], kind="mergesort")
        .reset_index(drop=True)
        if reference is not None and {"anaquel_1", "anaquel_2"}.issubset(reference.columns)
        else pd.DataFrame(columns=["anaquel_1", "anaquel_2"])
    )

    options = sorted(
        set(target["anaquel_1"].astype(str))
        | set(target["anaquel_2"].astype(str))
        | set(ref["anaquel_1"].astype(str))
        | set(ref["anaquel_2"].astype(str))
    )
    if not options:
        return pd.DataFrame(
            columns=[
                "organizacion",
                "prob_estimada",
                "ic_bajo",
                "ic_alto",
                "estabilidad_top1",
                "n",
            ]
        )

    target_w = _plackett_luce_weights(target, options)
    ref_w = _plackett_luce_weights(ref, options) if len(ref) else target_w.copy()

    n = len(target)
    lam = n / (n + float(shrink_strength)) if shrink_strength > 0 else 1.0
    est = lam * target_w + (1.0 - lam) * ref_w
    est /= est.sum()

    boot_vals = []
    if bootstrap > 0 and n >= 2:
        rng = np.random.default_rng(seed)
        values = target.reset_index(drop=True)
        for _ in range(int(bootstrap)):
            take = rng.integers(0, n, size=n)
            sample = values.iloc[take]
            bw = _plackett_luce_weights(sample, options)
            bw = lam * bw + (1.0 - lam) * ref_w
            bw /= bw.sum()
            boot_vals.append(bw)

    if boot_vals:
        arr = np.vstack(boot_vals)
        low = np.quantile(arr, 0.025, axis=0)
        high = np.quantile(arr, 0.975, axis=0)
        order = np.argsort(-arr, axis=1)
        winners = order[:, 0]
        stability = np.array([(winners == i).mean() for i in range(len(options))])

        # Mean bootstrap rank gives a smooth measure of consistency instead of a
        # binary Top-2 indicator. Rank 1 is best.
        rank_matrix = np.empty_like(order, dtype=float)
        row_idx = np.arange(order.shape[0])[:, None]
        rank_matrix[row_idx, order] = np.arange(1, len(options) + 1, dtype=float)
        mean_rank = rank_matrix.mean(axis=0)
    else:
        low = est.copy()
        high = est.copy()
        deterministic_order = np.argsort(-est)
        stability = np.zeros(len(options), dtype=float)
        stability[int(deterministic_order[0])] = 1.0
        mean_rank = np.empty(len(options), dtype=float)
        mean_rank[deterministic_order] = np.arange(1, len(options) + 1, dtype=float)

    # Continuous executive recommendation score (0-100).
    # 65% = relative Plackett-Luce worth versus the current leader.
    # 35% = bootstrap rank consistency. The final score is normalized so the
    # strongest option in the current selection equals 100.
    max_est = max(float(est.max()), 1e-12)
    relative_preference = est / max_est * 100.0
    if len(options) > 1:
        consistency_score = (len(options) - mean_rank) / (len(options) - 1) * 100.0
    else:
        consistency_score = np.array([100.0], dtype=float)
    consistency_score = np.clip(consistency_score, 0.0, 100.0)

    raw_recommendation = 0.65 * relative_preference + 0.35 * consistency_score
    max_raw = max(float(raw_recommendation.max()), 1e-12)
    recommendation_score = raw_recommendation / max_raw * 100.0

    out = pd.DataFrame({
        "organizacion": options,
        "nivel_recomendacion": recommendation_score,
        "preferencia_relativa": relative_preference,
        "consistencia": consistency_score,
        "posicion_media": mean_rank,
        "prob_estimada": est * 100,
        "ic_bajo": low * 100,
        "ic_alto": high * 100,
        "estabilidad_top1": stability * 100,
        "n": n,
    })
    return out.sort_values("nivel_recomendacion", ascending=False).reset_index(drop=True)


def shelf_conditional_model(
    df: pd.DataFrame,
    first_choice: str,
    reference: pd.DataFrame | None = None,
    *,
    strength: float = 8.0,
) -> pd.DataFrame:
    """Estimate P(A2=j | A1=first_choice) with empirical-Bayes smoothing.

    The prior comes from the reference conditional distribution when available;
    otherwise it falls back to the overall A2 distribution. A simple Wilson
    interval is returned using the effective sample size after smoothing.
    """
    first_choice = str(first_choice)
    target = df[["anaquel_1", "anaquel_2"]].dropna().copy()
    ref = (
        reference[["anaquel_1", "anaquel_2"]].dropna().copy()
        if reference is not None and {"anaquel_1", "anaquel_2"}.issubset(reference.columns)
        else pd.DataFrame(columns=["anaquel_1", "anaquel_2"])
    )

    options = sorted(
        (
            set(target["anaquel_1"].astype(str))
            | set(target["anaquel_2"].astype(str))
            | set(ref["anaquel_1"].astype(str))
            | set(ref["anaquel_2"].astype(str))
        ) - {first_choice}
    )
    if not options:
        return pd.DataFrame(
            columns=["organizacion", "prob_condicional", "ic_bajo", "ic_alto", "lift", "n_rama"]
        )

    subset = target[target["anaquel_1"].astype(str) == first_choice]
    counts = subset["anaquel_2"].astype(str).value_counts()
    n_branch = int(counts.sum())

    ref_subset = ref[ref["anaquel_1"].astype(str) == first_choice]
    if len(ref_subset):
        prior_counts = ref_subset["anaquel_2"].astype(str).value_counts()
    elif len(ref):
        prior_counts = ref["anaquel_2"].astype(str).value_counts()
    else:
        prior_counts = target["anaquel_2"].astype(str).value_counts()

    prior_vec = np.array([float(prior_counts.get(o, 0.0)) for o in options], dtype=float)
    if prior_vec.sum() <= 0:
        prior_vec = np.ones(len(options), dtype=float)
    prior_vec /= prior_vec.sum()

    obs = np.array([float(counts.get(o, 0.0)) for o in options], dtype=float)
    effective_n = float(n_branch) + float(strength)
    post = (obs + float(strength) * prior_vec) / max(effective_n, 1e-12)

    baseline_counts = target["anaquel_2"].astype(str).value_counts()
    baseline = np.array([float(baseline_counts.get(o, 0.0)) for o in options], dtype=float)
    if baseline.sum() <= 0:
        baseline = prior_vec.copy()
    else:
        baseline /= baseline.sum()

    # Wilson interval using the effective sample size of the smoothed estimate.
    z = 1.96
    denom = 1.0 + z * z / max(effective_n, 1.0)
    center = (post + z * z / (2.0 * max(effective_n, 1.0))) / denom
    half = (
        z
        * np.sqrt(
            np.maximum(
                post * (1.0 - post) / max(effective_n, 1.0)
                + z * z / (4.0 * max(effective_n, 1.0) ** 2),
                0.0,
            )
        )
        / denom
    )

    lift = np.divide(
        post,
        np.maximum(baseline, 1e-12),
        out=np.full(len(options), np.nan),
        where=baseline > 0,
    )

    out = pd.DataFrame({
        "organizacion": options,
        "prob_condicional": post * 100,
        "ic_bajo": np.maximum(0.0, center - half) * 100,
        "ic_alto": np.minimum(1.0, center + half) * 100,
        "lift": lift,
        "n_rama": n_branch,
    })
    return out.sort_values("prob_condicional", ascending=False).reset_index(drop=True)


def shelf_priority(df: pd.DataFrame) -> pd.DataFrame:
    opts=sorted(set(df["anaquel_1"].dropna()).union(set(df["anaquel_2"].dropna())))
    rows=[]; n=max(len(df),1)
    for o in opts:
        p1=(df["anaquel_1"]==o).mean()*100
        p2=(df["anaquel_2"]==o).mean()*100
        idx=(2*p1+p2)/3
        rows.append({"organizacion":o,"primera_ayuda":p1,"segunda_ayuda":p2,"indice_prioridad":idx})
    return pd.DataFrame(rows).sort_values("indice_prioridad",ascending=False).reset_index(drop=True)


def shelf_pair_score(df: pd.DataFrame, primary: str, secondary: str) -> dict:
    if len(df)==0: return {"exact_order":np.nan,"top2_any_order":np.nan,"coverage":np.nan}
    exact=((df["anaquel_1"]==primary)&(df["anaquel_2"]==secondary)).mean()*100
    unordered=(((df["anaquel_1"]==primary)&(df["anaquel_2"]==secondary))|((df["anaquel_1"]==secondary)&(df["anaquel_2"]==primary))).mean()*100
    coverage=((df["anaquel_1"].isin([primary,secondary]))|(df["anaquel_2"].isin([primary,secondary]))).mean()*100
    return {"exact_order":exact,"top2_any_order":unordered,"coverage":coverage}


def friction_summary(df: pd.DataFrame) -> tuple[float,pd.DataFrame]:
    easy=df["facilidad_encontrar"].isin(["Fácil","Muy fácil"]).mean()*100 if len(df) else np.nan
    barriers=pct_table(df["barrera_principal"],"barrera")
    return easy, barriers


def executive_kpis(df: pd.DataFrame) -> dict:
    d4_yes=(df["decision_validacion"]=="Sí").mean()*100 if len(df) else np.nan
    md=maxdiff_summary(df)
    top_driver=md.iloc[0]["driver"] if len(md) else None
    d1=pct_table(df["decision_1"],"criterio")
    first=d1.iloc[0]["criterio"] if len(d1) else None
    k=substitution_kpis(df)
    easy,_=friction_summary(df)
    return {"validacion_arbol":d4_yes,"primer_gate":first,"top_driver":top_driver,"facilidad":easy,**k}
