from __future__ import annotations

from dataclasses import dataclass
from math import lgamma
from typing import Iterable

import numpy as np
import pandas as pd


DEFAULT_STAGES = ("decision_1", "decision_2", "decision_3")


@dataclass(frozen=True)
class SequentialBayesConfig:
    """Runtime contract for the sequential Bayesian decision journey."""

    stages: tuple[str, str, str] = DEFAULT_STAGES
    validation_col: str = "decision_validacion"
    validation_yes_values: tuple[object, ...] = (1, "1", "Sí", "Si", "SI", "sí", "si")
    prior_grid: tuple[float, ...] = (
        0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0, 32.0, 48.0, 64.0
    )
    simulations: int = 10_000
    credible_level: float = 0.90
    random_seed: int = 20261007


@dataclass
class SequentialBayesFit:
    categories: list[str]
    stage1_alpha: np.ndarray
    stage2_alpha: dict[str, np.ndarray]
    stage3_alpha: dict[tuple[str, str], np.ndarray]
    stage1_counts: np.ndarray
    stage2_counts: dict[str, np.ndarray]
    stage3_counts: dict[tuple[str, str], np.ndarray]
    kappa: dict[str, float]
    n_complete: int
    qa: dict[str, int | float]
    config: SequentialBayesConfig

    def stage1_mean(self) -> np.ndarray:
        return self.stage1_alpha / self.stage1_alpha.sum()

    def stage2_mean(self, first: str) -> np.ndarray:
        a = self.stage2_alpha[first]
        return a / a.sum()

    def stage3_mean(self, first: str, second: str) -> np.ndarray:
        a = self.stage3_alpha[(first, second)]
        return a / a.sum()


def _clean_string(s: pd.Series) -> pd.Series:
    return s.dropna().astype(str).str.strip()


def validate_sequence_dataframe(
    df: pd.DataFrame,
    *,
    stages: tuple[str, str, str] = DEFAULT_STAGES,
) -> dict[str, int | float]:
    """Validate completeness and structural no-repeat rules in D1/D2/D3."""
    missing = [c for c in stages if c not in df.columns]
    if missing:
        raise ValueError("Missing required decision variables: " + ", ".join(missing))

    d = df[list(stages)].copy()
    complete = d.dropna().copy()
    for c in stages:
        complete[c] = complete[c].astype(str).str.strip()

    repeat_12 = int((complete[stages[0]] == complete[stages[1]]).sum())
    repeat_13 = int((complete[stages[0]] == complete[stages[2]]).sum())
    repeat_23 = int((complete[stages[1]] == complete[stages[2]]).sum())
    invalid = int(((complete[stages[0]] == complete[stages[1]]) |
                   (complete[stages[0]] == complete[stages[2]]) |
                   (complete[stages[1]] == complete[stages[2]])).sum())
    return {
        "n_total": int(len(df)),
        "n_complete": int(len(complete)),
        "complete_pct": float(len(complete) / len(df) * 100) if len(df) else 0.0,
        "repeat_d1_d2": repeat_12,
        "repeat_d1_d3": repeat_13,
        "repeat_d2_d3": repeat_23,
        "invalid_sequences": invalid,
    }


def _categories_from_data(df: pd.DataFrame, stages: tuple[str, str, str]) -> list[str]:
    cats: set[str] = set()
    for c in stages:
        cats.update(_clean_string(df[c]).tolist())
    return sorted(cats, key=lambda x: x.casefold())


def _count_vector(series: pd.Series, categories: list[str]) -> np.ndarray:
    counts = _clean_string(series).value_counts()
    return np.array([float(counts.get(c, 0.0)) for c in categories], dtype=float)


def _normalize_on_allowed(base: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    out = np.zeros_like(base, dtype=float)
    b = np.asarray(base, dtype=float).copy()
    b[~allowed] = 0.0
    total = b.sum()
    if total <= 0:
        n_allowed = int(allowed.sum())
        if n_allowed:
            out[allowed] = 1.0 / n_allowed
        return out
    out[allowed] = b[allowed] / total
    return out


def _log_dm_marginal(counts: np.ndarray, alpha: np.ndarray, allowed: np.ndarray) -> float:
    n = counts[allowed]
    a = alpha[allowed]
    if len(a) == 0 or np.any(a <= 0):
        return float("-inf")
    n_sum = float(n.sum())
    a_sum = float(a.sum())
    out = lgamma(a_sum) - lgamma(a_sum + n_sum)
    out += sum(lgamma(float(ai + ni)) - lgamma(float(ai)) for ai, ni in zip(a, n))
    return float(out)


def _estimate_kappa(
    groups: list[tuple[np.ndarray, np.ndarray, np.ndarray]],
    grid: Iterable[float],
) -> float:
    """Empirical-Bayes concentration chosen by marginal likelihood."""
    best_k = None
    best_ll = float("-inf")
    for k in grid:
        k = float(k)
        ll = 0.0
        for counts, prior_p, allowed in groups:
            p = _normalize_on_allowed(prior_p, allowed)
            alpha = np.where(allowed, np.maximum(k * p, 1e-9), 0.0)
            ll += _log_dm_marginal(counts, alpha, allowed)
        if ll > best_ll:
            best_ll = ll
            best_k = k
    return float(best_k if best_k is not None else 1.0)


def _prepare_valid_sequences(
    df: pd.DataFrame,
    stages: tuple[str, str, str],
) -> pd.DataFrame:
    d1, d2, d3 = stages
    data = df[[d1, d2, d3]].dropna().copy()
    for c in stages:
        data[c] = data[c].astype(str).str.strip()
    return data[
        (data[d1] != data[d2]) &
        (data[d1] != data[d3]) &
        (data[d2] != data[d3])
    ].copy()


def fit_sequential_bayes(
    df: pd.DataFrame,
    *,
    prior_df: pd.DataFrame | None = None,
    config: SequentialBayesConfig | None = None,
) -> SequentialBayesFit:
    """Fit D1 -> D2|D1 -> D3|D1,D2 using hierarchical empirical Bayes.

    df is the target population shown in the dashboard. prior_df is an
    optional broader reference population used only to construct the prior.
    When omitted, the target itself supplies the empirical prior.
    """
    cfg = config or SequentialBayesConfig()
    d1, d2, d3 = cfg.stages
    qa = validate_sequence_dataframe(df, stages=cfg.stages)

    data = _prepare_valid_sequences(df, cfg.stages)
    if data.empty:
        raise ValueError("No valid complete D1/D2/D3 sequences are available.")

    prior_source = prior_df if prior_df is not None and len(prior_df) else df
    if any(c not in prior_source.columns for c in cfg.stages):
        prior_source = df
    prior_data = _prepare_valid_sequences(prior_source, cfg.stages)
    if prior_data.empty:
        prior_data = data.copy()

    cats = sorted(
        set(_categories_from_data(data, cfg.stages)).union(
            _categories_from_data(prior_data, cfg.stages)
        ),
        key=lambda x: x.casefold(),
    )
    idx = {c: i for i, c in enumerate(cats)}
    k = len(cats)

    # D1 prior: broader reference distribution.
    c1 = _count_vector(data[d1], cats)
    prior1_counts = _count_vector(prior_data[d1], cats)
    prior1_p = prior1_counts / prior1_counts.sum() if prior1_counts.sum() else np.repeat(1.0 / k, k)
    k1 = _estimate_kappa(
        [(c1, prior1_p, np.ones(k, dtype=bool))],
        cfg.prior_grid,
    )
    a1 = c1 + k1 * prior1_p

    # D2 prior: prefer P(D2|D1) in broader reference, fallback to global D2.
    global2 = _count_vector(prior_data[d2], cats)
    global2_p = global2 / global2.sum() if global2.sum() else np.repeat(1.0 / k, k)

    stage2_counts: dict[str, np.ndarray] = {}
    stage2_prior: dict[str, np.ndarray] = {}
    stage2_groups: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    for first in cats:
        sub = data[data[d1] == first]
        counts = _count_vector(sub[d2], cats)
        allowed = np.ones(k, dtype=bool)
        allowed[idx[first]] = False

        prior_sub = prior_data[prior_data[d1] == first]
        prior_counts = _count_vector(prior_sub[d2], cats)
        prior_p = prior_counts / prior_counts.sum() if prior_counts.sum() else global2_p
        prior_p = _normalize_on_allowed(prior_p, allowed)

        stage2_counts[first] = counts
        stage2_prior[first] = prior_p
        stage2_groups.append((counts, prior_p, allowed))
    k2 = _estimate_kappa(stage2_groups, cfg.prior_grid)

    stage2_alpha: dict[str, np.ndarray] = {}
    for first in cats:
        allowed = np.ones(k, dtype=bool)
        allowed[idx[first]] = False
        alpha = stage2_counts[first] + k2 * stage2_prior[first]
        alpha[~allowed] = 0.0
        stage2_alpha[first] = alpha

    # D3 prior: prefer P(D3|D1,D2), fallback to P(D3|D1), then global D3.
    global3 = _count_vector(prior_data[d3], cats)
    global3_p = global3 / global3.sum() if global3.sum() else np.repeat(1.0 / k, k)

    stage3_counts: dict[tuple[str, str], np.ndarray] = {}
    stage3_prior: dict[tuple[str, str], np.ndarray] = {}
    stage3_groups: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []

    for first in cats:
        prior_first = prior_data[prior_data[d1] == first]
        prior_first_counts = _count_vector(prior_first[d3], cats)
        prior_first_p = prior_first_counts / prior_first_counts.sum() if prior_first_counts.sum() else global3_p

        for second in cats:
            if second == first:
                continue
            sub = data[(data[d1] == first) & (data[d2] == second)]
            counts = _count_vector(sub[d3], cats)
            allowed = np.ones(k, dtype=bool)
            allowed[idx[first]] = False
            allowed[idx[second]] = False

            prior_pair = prior_data[
                (prior_data[d1] == first) & (prior_data[d2] == second)
            ]
            prior_pair_counts = _count_vector(prior_pair[d3], cats)
            prior_p = prior_pair_counts / prior_pair_counts.sum() if prior_pair_counts.sum() else prior_first_p
            prior_p = _normalize_on_allowed(prior_p, allowed)

            key = (first, second)
            stage3_counts[key] = counts
            stage3_prior[key] = prior_p
            stage3_groups.append((counts, prior_p, allowed))

    k3 = _estimate_kappa(stage3_groups, cfg.prior_grid)

    stage3_alpha: dict[tuple[str, str], np.ndarray] = {}
    for key, counts in stage3_counts.items():
        first, second = key
        allowed = np.ones(k, dtype=bool)
        allowed[idx[first]] = False
        allowed[idx[second]] = False
        alpha = counts + k3 * stage3_prior[key]
        alpha[~allowed] = 0.0
        stage3_alpha[key] = alpha

    return SequentialBayesFit(
        categories=cats,
        stage1_alpha=a1,
        stage2_alpha=stage2_alpha,
        stage3_alpha=stage3_alpha,
        stage1_counts=c1,
        stage2_counts=stage2_counts,
        stage3_counts=stage3_counts,
        kappa={"d1": k1, "d2": k2, "d3": k3},
        n_complete=int(len(data)),
        qa=qa,
        config=cfg,
    )


def _sample_allowed_dirichlet(
    rng: np.random.Generator,
    alpha: np.ndarray,
    n: int,
) -> np.ndarray:
    allowed = alpha > 0
    out = np.zeros((n, len(alpha)), dtype=float)
    if allowed.any():
        out[:, allowed] = rng.dirichlet(alpha[allowed], size=n)
    return out


def posterior_route_summary(
    fit: SequentialBayesFit,
    *,
    simulations: int | None = None,
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Monte-Carlo posterior summary for every valid full D1->D2->D3 route."""
    sims = int(simulations or fit.config.simulations)
    seed = fit.config.random_seed if random_seed is None else int(random_seed)
    rng = np.random.default_rng(seed)
    cats = fit.categories
    idx = {c: i for i, c in enumerate(cats)}
    level = float(fit.config.credible_level)
    q_lo = (1.0 - level) / 2.0
    q_hi = 1.0 - q_lo

    p1_s = _sample_allowed_dirichlet(rng, fit.stage1_alpha, sims)
    p2_s = {
        first: _sample_allowed_dirichlet(rng, fit.stage2_alpha[first], sims)
        for first in cats
    }
    p3_s = {
        key: _sample_allowed_dirichlet(rng, alpha, sims)
        for key, alpha in fit.stage3_alpha.items()
    }

    route_defs: list[tuple[str, str, str]] = []
    route_sims: list[np.ndarray] = []
    for first in cats:
        i = idx[first]
        for second in cats:
            if second == first:
                continue
            j = idx[second]
            key = (first, second)
            if key not in p3_s:
                continue
            for third in cats:
                if third in (first, second):
                    continue
                h = idx[third]
                prob = p1_s[:, i] * p2_s[first][:, j] * p3_s[key][:, h]
                route_defs.append((first, second, third))
                route_sims.append(prob)

    if not route_sims:
        return pd.DataFrame()

    mat = np.column_stack(route_sims)
    winner = np.argmax(mat, axis=1)
    top1_counts = np.bincount(winner, minlength=mat.shape[1])

    rows = []
    for r_idx, (first, second, third) in enumerate(route_defs):
        vals = mat[:, r_idx]
        branch2_n = int(fit.stage2_counts[first].sum())
        branch3_n = int(fit.stage3_counts[(first, second)].sum())
        rows.append({
            "first": first,
            "second": second,
            "third": third,
            "route": f"{first} → {second} → {third}",
            "posterior_mean_pct": float(vals.mean() * 100),
            "ci_low_pct": float(np.quantile(vals, q_lo) * 100),
            "ci_high_pct": float(np.quantile(vals, q_hi) * 100),
            "p_top1_pct": float(top1_counts[r_idx] / sims * 100),
            "base_d1": int(fit.n_complete),
            "base_d2": branch2_n,
            "base_d3": branch3_n,
        })
    out = pd.DataFrame(rows).sort_values(
        ["posterior_mean_pct", "p_top1_pct"], ascending=[False, False]
    ).reset_index(drop=True)
    out.insert(0, "rank", np.arange(1, len(out) + 1))
    return out


def posterior_node_summary(fit: SequentialBayesFit) -> dict[str, pd.DataFrame]:
    """Posterior means for D1 and conditional transitions D2/D3."""
    cats = fit.categories
    p1 = fit.stage1_mean()
    d1 = pd.DataFrame({
        "criterion": cats,
        "posterior_pct": p1 * 100,
        "base": fit.n_complete,
    }).sort_values("posterior_pct", ascending=False).reset_index(drop=True)

    rows2 = []
    for first in cats:
        p = fit.stage2_mean(first)
        base = int(fit.stage2_counts[first].sum())
        for j, second in enumerate(cats):
            if second == first:
                continue
            rows2.append({
                "first": first,
                "second": second,
                "conditional_pct": float(p[j] * 100),
                "base": base,
            })

    rows3 = []
    for (first, second), alpha in fit.stage3_alpha.items():
        p = alpha / alpha.sum()
        base = int(fit.stage3_counts[(first, second)].sum())
        for h, third in enumerate(cats):
            if third in (first, second):
                continue
            rows3.append({
                "first": first,
                "second": second,
                "third": third,
                "conditional_pct": float(p[h] * 100),
                "base": base,
            })

    return {
        "d1": d1,
        "d2": pd.DataFrame(rows2).sort_values(
            ["first", "conditional_pct"], ascending=[True, False]
        ).reset_index(drop=True),
        "d3": pd.DataFrame(rows3).sort_values(
            ["first", "second", "conditional_pct"], ascending=[True, True, False]
        ).reset_index(drop=True),
    }


def base_certainty_score(n: int) -> float:
    if n >= 200:
        return 100.0
    if n >= 100:
        return 85.0
    if n >= 60:
        return 70.0
    if n >= 30:
        return 50.0
    return 20.0


def certainty_label(score: float, min_branch_n: int) -> str:
    if min_branch_n < 30:
        return "NO CONCLUYENTE"
    if score >= 85:
        return "ALTA"
    if score >= 70:
        return "MEDIA"
    if score >= 55:
        return "DIRECCIONAL"
    return "NO CONCLUYENTE"


def route_prior_robustness(
    df: pd.DataFrame,
    route: tuple[str, str, str],
    *,
    prior_df: pd.DataFrame | None = None,
    config: SequentialBayesConfig | None = None,
) -> float:
    """Score 0-100 based on route stability under weaker/stronger prior grids."""
    cfg = config or SequentialBayesConfig()
    base_fit = fit_sequential_bayes(df, prior_df=prior_df, config=cfg)
    base = posterior_route_summary(base_fit, simulations=min(2500, cfg.simulations))
    base_row = base[
        (base["first"] == route[0]) &
        (base["second"] == route[1]) &
        (base["third"] == route[2])
    ]
    if base_row.empty:
        return 0.0
    base_p = float(base_row.iloc[0]["posterior_mean_pct"])

    scores = []
    for factor in (0.5, 2.0):
        grid = tuple(max(0.05, x * factor) for x in cfg.prior_grid)
        alt_cfg = SequentialBayesConfig(
            stages=cfg.stages,
            validation_col=cfg.validation_col,
            validation_yes_values=cfg.validation_yes_values,
            prior_grid=grid,
            simulations=min(2500, cfg.simulations),
            credible_level=cfg.credible_level,
            random_seed=cfg.random_seed + int(factor * 10),
        )
        alt_fit = fit_sequential_bayes(df, prior_df=prior_df, config=alt_cfg)
        alt = posterior_route_summary(alt_fit, simulations=alt_cfg.simulations)
        alt_row = alt[
            (alt["first"] == route[0]) &
            (alt["second"] == route[1]) &
            (alt["third"] == route[2])
        ]
        if alt_row.empty:
            scores.append(0.0)
            continue
        alt_p = float(alt_row.iloc[0]["posterior_mean_pct"])
        rel_delta = abs(alt_p - base_p) / max(base_p, 1e-9)
        score = max(0.0, 100.0 * (1.0 - rel_delta / 0.35))
        scores.append(score)
    return float(np.mean(scores)) if scores else 0.0


def d4_consistency_score(
    df: pd.DataFrame,
    route: tuple[str, str, str],
    *,
    prior_df: pd.DataFrame | None = None,
    config: SequentialBayesConfig | None = None,
) -> float:
    """Compare the route posterior in total vs respondents validating D1->D2->D3."""
    cfg = config or SequentialBayesConfig()
    if cfg.validation_col not in df.columns:
        return 50.0

    yes = df[df[cfg.validation_col].isin(cfg.validation_yes_values)].copy()
    if len(yes) < 30:
        return 50.0

    total_fit = fit_sequential_bayes(df, prior_df=prior_df, config=cfg)
    yes_fit = fit_sequential_bayes(yes, prior_df=prior_df, config=cfg)
    total = posterior_route_summary(total_fit, simulations=min(2500, cfg.simulations))
    valid = posterior_route_summary(yes_fit, simulations=min(2500, cfg.simulations))

    def pick(t):
        row = t[
            (t["first"] == route[0]) &
            (t["second"] == route[1]) &
            (t["third"] == route[2])
        ]
        return None if row.empty else row.iloc[0]

    a, b = pick(total), pick(valid)
    if a is None or b is None:
        return 0.0

    p_total = float(a["posterior_mean_pct"])
    p_yes = float(b["posterior_mean_pct"])
    rel_delta = abs(p_yes - p_total) / max(p_total, 1e-9)
    prob_score = max(0.0, 100.0 * (1.0 - rel_delta / 0.40))

    rank_total = int(a["rank"])
    rank_yes = int(b["rank"])
    rank_gap = abs(rank_total - rank_yes)
    rank_score = max(0.0, 100.0 - 15.0 * rank_gap)
    return float(0.6 * prob_score + 0.4 * rank_score)


def journey_confidence_score(
    df: pd.DataFrame,
    fit: SequentialBayesFit,
    routes: pd.DataFrame,
    *,
    prior_df: pd.DataFrame | None = None,
    config: SequentialBayesConfig | None = None,
) -> pd.DataFrame:
    """Attach JCS to routes; full diagnostics are computed for the leading 10."""
    cfg = config or fit.config
    if routes.empty:
        return routes.copy()

    out = routes.copy()
    jcs, labels, robustness, d4_scores, base_scores = [], [], [], [], []

    for _, row in out.iterrows():
        route = (str(row["first"]), str(row["second"]), str(row["third"]))
        min_base = int(min(row["base_d2"], row["base_d3"]))
        b_score = base_certainty_score(min_base)

        if int(row["rank"]) <= 10:
            r_score = route_prior_robustness(df, route, prior_df=prior_df, config=cfg)
            d_score = d4_consistency_score(df, route, prior_df=prior_df, config=cfg)
        else:
            r_score = np.nan
            d_score = np.nan

        if np.isfinite(r_score) and np.isfinite(d_score):
            score = (
                0.45 * float(row["p_top1_pct"])
                + 0.20 * r_score
                + 0.20 * d_score
                + 0.15 * b_score
            )
            label = certainty_label(score, min_base)
        else:
            score = np.nan
            label = ""

        jcs.append(score)
        labels.append(label)
        robustness.append(r_score)
        d4_scores.append(d_score)
        base_scores.append(b_score)

    out["prior_robustness_score"] = robustness
    out["d4_consistency_score"] = d4_scores
    out["base_score"] = base_scores
    out["jcs"] = jcs
    out["certainty"] = labels
    return out
