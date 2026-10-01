from __future__ import annotations

from math import sqrt
from statistics import NormalDist

import numpy as np
import pandas as pd

PRIOR_STRENGTH = 20.0
MIN_TENDENTIAL_N = 10
MAX_TENDENTIAL_N = 59
Z90 = NormalDist().inv_cdf(0.95)

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


def tendential_eligible(n: int) -> bool:
    return MIN_TENDENTIAL_N <= int(n) <= MAX_TENDENTIAL_N


def _clean(series: pd.Series) -> pd.Series:
    return series.dropna().astype(str)


def categorical_tendential(
    target: pd.DataFrame,
    reference: pd.DataFrame,
    col: str,
    *,
    strength: float = PRIOR_STRENGTH,
    label_name: str = "categoria",
) -> pd.DataFrame:
    """Empirical-Bayes / Dirichlet partial pooling for a categorical variable."""
    t = _clean(target[col])
    r = _clean(reference[col])
    cats = sorted(set(t.unique()).union(set(r.unique())))
    if not cats:
        return pd.DataFrame(columns=[label_name, "n", "observado", "tendencial", "referencia", "rango_bajo", "rango_alto"])

    counts = t.value_counts().reindex(cats, fill_value=0).astype(float)
    if len(r):
        ref_p = r.value_counts(normalize=True).reindex(cats, fill_value=0).astype(float)
    else:
        ref_p = pd.Series(np.repeat(1 / len(cats), len(cats)), index=cats)

    n = float(len(t))
    alpha0 = ref_p * float(strength)
    alpha = counts + alpha0
    alpha_sum = float(alpha.sum())
    posterior = alpha / alpha_sum if alpha_sum else alpha * np.nan
    observed = counts / n if n else counts * np.nan

    rows = []
    for cat in cats:
        a = float(alpha.loc[cat])
        b = max(alpha_sum - a, 1e-9)
        p = float(posterior.loc[cat])
        var = (a * b) / (((a + b) ** 2) * (a + b + 1)) if (a + b) > 0 else np.nan
        se = sqrt(max(var, 0.0)) if np.isfinite(var) else np.nan
        lo = max(0.0, p - Z90 * se) if np.isfinite(se) else np.nan
        hi = min(1.0, p + Z90 * se) if np.isfinite(se) else np.nan
        rows.append({
            label_name: cat,
            "n": int(counts.loc[cat]),
            "observado": float(observed.loc[cat]) * 100 if n else np.nan,
            "tendencial": p * 100,
            "referencia": float(ref_p.loc[cat]) * 100,
            "rango_bajo": lo * 100,
            "rango_alto": hi * 100,
        })
    return pd.DataFrame(rows).sort_values("tendencial", ascending=False).reset_index(drop=True)


def binary_tendential(
    target: pd.DataFrame,
    reference: pd.DataFrame,
    col: str,
    success_values: set,
    *,
    strength: float = PRIOR_STRENGTH,
) -> dict:
    t = target[col].dropna()
    r = reference[col].dropna()
    n = len(t)
    k = int(t.isin(success_values).sum())
    p_ref = float(r.isin(success_values).mean()) if len(r) else 0.5

    a = k + p_ref * strength
    b = (n - k) + (1 - p_ref) * strength
    p = a / (a + b)
    var = (a * b) / (((a + b) ** 2) * (a + b + 1))
    se = sqrt(max(var, 0.0))
    return {
        "n": int(n),
        "observado": (k / n * 100) if n else np.nan,
        "tendencial": p * 100,
        "referencia": p_ref * 100,
        "rango_bajo": max(0.0, p - Z90 * se) * 100,
        "rango_alto": min(1.0, p + Z90 * se) * 100,
    }


def tendential_kpis(target: pd.DataFrame, reference: pd.DataFrame) -> dict:
    valid = binary_tendential(target, reference, "decision_validacion_code", {1})
    brand = binary_tendential(target, reference, "sust_marca_code", {1, 2, 3, 4})
    tone = binary_tendential(target, reference, "sust_tono_code", {2})
    promo = binary_tendential(target, reference, "sust_promocion_code", {1})
    d1 = categorical_tendential(target, reference, "decision_1", label_name="criterio")
    md = maxdiff_tendential(target, reference)
    return {
        "validacion_arbol": valid["tendencial"],
        "validacion_arbol_rango": (valid["rango_bajo"], valid["rango_alto"]),
        "primer_gate": d1.iloc[0]["criterio"] if len(d1) else None,
        "primer_gate_pct": float(d1.iloc[0]["tendencial"]) if len(d1) else np.nan,
        "top_driver": md.iloc[0]["driver"] if len(md) else None,
        "top_driver_score": float(md.iloc[0]["tendencial"]) if len(md) else np.nan,
        "cambia_marca_si_falta_marca": brand["tendencial"],
        "cambia_marca_si_falta_marca_rango": (brand["rango_bajo"], brand["rango_alto"]),
        "cambia_marca_para_conservar_tono": tone["tendencial"],
        "cambia_marca_para_conservar_tono_rango": (tone["rango_bajo"], tone["rango_alto"]),
        "compra_sin_promocion": promo["tendencial"],
        "compra_sin_promocion_rango": (promo["rango_bajo"], promo["rango_alto"]),
    }


def decision_stage_tendential(target: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for stage, col in [("Primero", "decision_1"), ("Después", "decision_2"), ("Cierre", "decision_3")]:
        t = categorical_tendential(target, reference, col, label_name="criterio")
        t.insert(0, "etapa", stage)
        frames.append(t)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def maxdiff_tendential(
    target: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    strength: float = PRIOR_STRENGTH,
) -> pd.DataFrame:
    rows = []
    for col, label in MD_LABELS.items():
        ts = pd.to_numeric(target[col], errors="coerce").dropna()
        rs = pd.to_numeric(reference[col], errors="coerce").dropna()
        if len(ts) == 0:
            continue
        obs = float(ts.mean())
        ref = float(rs.mean()) if len(rs) else obs
        n = float(len(ts))
        trend = (n * obs + strength * ref) / (n + strength)
        rows.append({
            "driver": label,
            "n": int(n),
            "observado": obs,
            "tendencial": trend,
            "referencia": ref,
            "delta_vs_referencia": trend - ref,
        })
    return pd.DataFrame(rows).sort_values("tendencial", ascending=False).reset_index(drop=True)


def substitution_tendential(
    target: pd.DataFrame,
    reference: pd.DataFrame,
    scenario: str,
) -> pd.DataFrame:
    col = {
        "Marca no disponible": "sust_marca",
        "Tono/color no disponible": "sust_tono",
        "Sin promoción": "sust_promocion",
    }[scenario]
    return categorical_tendential(target, reference, col, label_name="respuesta")


def shelf_priority_tendential(target: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    a1 = categorical_tendential(target, reference, "anaquel_1", label_name="organizacion")
    a2 = categorical_tendential(target, reference, "anaquel_2", label_name="organizacion")
    a = a1[["organizacion", "observado", "tendencial"]].rename(
        columns={"observado": "primera_observada", "tendencial": "primera_tendencial"}
    )
    b = a2[["organizacion", "observado", "tendencial"]].rename(
        columns={"observado": "segunda_observada", "tendencial": "segunda_tendencial"}
    )
    out = a.merge(b, on="organizacion", how="outer").fillna(0)
    out["indice_observado"] = (2 * out["primera_observada"] + out["segunda_observada"]) / 3
    out["indice_tendencial"] = (2 * out["primera_tendencial"] + out["segunda_tendencial"]) / 3
    return out.sort_values("indice_tendencial", ascending=False).reset_index(drop=True)


def _posterior_prob(target_series: pd.Series, reference_series: pd.Series, strength: float) -> pd.DataFrame:
    temp_t = pd.DataFrame({"x": target_series})
    temp_r = pd.DataFrame({"x": reference_series})
    return categorical_tendential(temp_t, temp_r, "x", strength=strength, label_name="x")


def tree_links_tendential(
    target: pd.DataFrame,
    reference: pd.DataFrame,
    first_choice: str | None = None,
    *,
    top_d1: int = 5,
    top_d2: int = 5,
    top_d3: int = 4,
) -> dict:
    """Build a Sankey using smoothed conditional probabilities, scaled to the real target n."""
    n_target = max(len(target), 1)
    labels = ["Compra"]
    source, target_idx, value, custom = [], [], [], []
    node_idx = {"ROOT": 0}

    d1_dist = _posterior_prob(target["decision_1"], reference["decision_1"], PRIOR_STRENGTH)
    if first_choice and first_choice != "Todos":
        d1_dist = d1_dist[d1_dist["x"] == first_choice]
    else:
        d1_dist = d1_dist.head(top_d1)

    for _, r1 in d1_dist.iterrows():
        d1 = r1["x"]
        v1 = n_target * float(r1["tendencial"]) / 100
        key1 = f"D1|{d1}"
        node_idx[key1] = len(labels)
        labels.append(f"1º {d1}")
        source.append(0); target_idx.append(node_idx[key1]); value.append(v1)
        custom.append(f"Tendencial {r1['tendencial']:.1f}% · observado {r1['observado']:.1f}%")

        t1 = target[target["decision_1"] == d1]
        r1df = reference[reference["decision_1"] == d1]
        if len(r1df) == 0:
            r1df = reference
        d2_dist = _posterior_prob(t1["decision_2"], r1df["decision_2"], 12.0).head(top_d2)

        for _, r2 in d2_dist.iterrows():
            d2 = r2["x"]
            v2 = v1 * float(r2["tendencial"]) / 100
            key2 = f"D2|{d1}|{d2}"
            node_idx[key2] = len(labels)
            labels.append(f"2º {d2}")
            source.append(node_idx[key1]); target_idx.append(node_idx[key2]); value.append(v2)
            custom.append(f"Tendencial {r2['tendencial']:.1f}% dentro de la rama · observado {r2['observado']:.1f}%")

            t2 = t1[t1["decision_2"] == d2]
            r2df = r1df[r1df["decision_2"] == d2]
            if len(r2df) == 0:
                r2df = r1df
            d3_dist = _posterior_prob(t2["decision_3"], r2df["decision_3"], 8.0).head(top_d3)

            for _, r3 in d3_dist.iterrows():
                d3 = r3["x"]
                v3 = v2 * float(r3["tendencial"]) / 100
                key3 = f"D3|{d1}|{d2}|{d3}"
                node_idx[key3] = len(labels)
                labels.append(f"3º {d3}")
                source.append(node_idx[key2]); target_idx.append(node_idx[key3]); value.append(v3)
                custom.append(f"Tendencial {r3['tendencial']:.1f}% dentro de la rama · observado {r3['observado']:.1f}%")

    return {"labels": labels, "source": source, "target": target_idx, "value": value, "custom": custom}
