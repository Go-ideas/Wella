from __future__ import annotations

import pandas as pd

from engine import shelf_conditional_model, shelf_statistical_model


def _sample() -> pd.DataFrame:
    rows = []
    rows += [{"anaquel_1": "Necesidad", "anaquel_2": "Tono"}] * 30
    rows += [{"anaquel_1": "Necesidad", "anaquel_2": "Marca"}] * 10
    rows += [{"anaquel_1": "Tono", "anaquel_2": "Necesidad"}] * 18
    rows += [{"anaquel_1": "Marca", "anaquel_2": "Tono"}] * 8
    rows += [{"anaquel_1": "Beneficios", "anaquel_2": "Necesidad"}] * 4
    return pd.DataFrame(rows)


def test_shelf_statistical_model_ranks_dominant_first_choice():
    df = _sample()
    out = shelf_statistical_model(df, df, shrink_strength=0, bootstrap=60, seed=123)
    assert len(out) >= 4
    assert out.iloc[0]["organizacion"] == "Necesidad"
    assert 0 <= out.iloc[0]["ic_bajo"] <= out.iloc[0]["prob_estimada"] <= out.iloc[0]["ic_alto"] <= 100
    assert 0 <= out.iloc[0]["estabilidad_top1"] <= 100
    assert out.iloc[0]["nivel_recomendacion"] == 100
    assert 0 <= out.iloc[0]["consistencia"] <= 100
    assert 0 <= out.iloc[0]["preferencia_relativa"] <= 100


def test_shelf_conditional_model_recommends_tone_after_need():
    df = _sample()
    out = shelf_conditional_model(df, "Necesidad", df, strength=4)
    assert len(out) >= 3
    assert out.iloc[0]["organizacion"] == "Tono"
    assert out.iloc[0]["prob_condicional"] > out.iloc[1]["prob_condicional"]
    assert out.iloc[0]["lift"] > 1


def test_shelf_models_are_deterministic():
    df = _sample()
    a = shelf_statistical_model(df, df, shrink_strength=8, bootstrap=40, seed=20261001)
    b = shelf_statistical_model(df, df, shrink_strength=8, bootstrap=40, seed=20261001)
    pd.testing.assert_frame_equal(a, b)
