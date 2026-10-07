from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bayesian_journey import (
    SequentialBayesConfig,
    fit_sequential_bayes,
    posterior_route_summary,
    validate_sequence_dataframe,
)


def _synthetic(n=600, seed=7):
    rng = np.random.default_rng(seed)
    cats = ["Tono", "Precio", "Beneficios", "Disponible", "Marca"]
    rows = []
    for _ in range(n):
        d1 = rng.choice(cats, p=[0.45, 0.18, 0.15, 0.12, 0.10])
        remaining = [c for c in cats if c != d1]

        if d1 == "Tono":
            weights = {
                "Precio": 0.40,
                "Beneficios": 0.25,
                "Marca": 0.20,
                "Disponible": 0.15,
            }
            p2 = np.array([weights[c] for c in remaining], dtype=float)
        else:
            p2 = np.ones(len(remaining), dtype=float)
        p2 /= p2.sum()
        d2 = rng.choice(remaining, p=p2)

        remaining3 = [c for c in cats if c not in (d1, d2)]
        if d1 == "Tono" and d2 == "Precio":
            weights3 = {"Disponible": 0.50, "Marca": 0.30, "Beneficios": 0.20}
            p3 = np.array([weights3.get(c, 1.0) for c in remaining3], dtype=float)
        else:
            p3 = np.ones(len(remaining3), dtype=float)
        p3 /= p3.sum()
        d3 = rng.choice(remaining3, p=p3)

        rows.append((d1, d2, d3, 1 if rng.random() < 0.92 else 2))

    return pd.DataFrame(
        rows,
        columns=[
            "decision_1",
            "decision_2",
            "decision_3",
            "decision_validacion_code",
        ],
    )


def test_sequence_qa_has_no_repeats():
    df = _synthetic()
    qa = validate_sequence_dataframe(df)
    assert qa["n_complete"] == len(df)
    assert qa["invalid_sequences"] == 0


def test_bayesian_model_identifies_known_path():
    df = _synthetic()
    cfg = SequentialBayesConfig(simulations=1200, random_seed=11)
    fit = fit_sequential_bayes(df, config=cfg)
    routes = posterior_route_summary(fit, simulations=1200, random_seed=11)

    top = routes.iloc[0]
    assert top["first"] == "Tono"
    assert top["second"] == "Precio"
    assert top["third"] == "Disponible"
    assert top["posterior_mean_pct"] > 0
    assert top["ci_low_pct"] < top["posterior_mean_pct"] < top["ci_high_pct"]


def test_structural_repeats_are_excluded():
    df = _synthetic()
    cfg = SequentialBayesConfig(simulations=300)
    fit = fit_sequential_bayes(df, config=cfg)
    routes = posterior_route_summary(fit, simulations=300)

    assert not (routes["first"] == routes["second"]).any()
    assert not (routes["first"] == routes["third"]).any()
    assert not (routes["second"] == routes["third"]).any()
