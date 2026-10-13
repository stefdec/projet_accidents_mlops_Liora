from __future__ import annotations

import pandas as pd
import pytest

from src.train_api.features import AccidentFeatureTransformer


def prepared_rows() -> pd.DataFrame:
    rows = 10
    return pd.DataFrame(
        {
            "Num_Acc": list(range(rows)),
            "accident_date": pd.date_range("2023-01-01", periods=rows),
            "year": [2023] * rows,
            "month": [1] * rows,
            "day_of_week": ["Monday", "Tuesday"] * 5,
            "day_period": ["matin", "soir"] * 5,
            "age": [20, 22, 30, 35, 45, 50, 65, 70, 80, 25],
            "catv_group": ["Véhicules légers"] * rows,
            "macro_choc": ["Frontal"] * rows,
            "macro_obsm": ["Vehicule"] * rows,
            "type_crash": ["Vehicule_vs_Vehicule"] * rows,
            "presence_obstacle_fixe": ["Non/Inconnu"] * rows,
            "lat": [43 + index / 10 for index in range(rows)],
            "long": [1 + index / 10 for index in range(rows)],
            "vma": [50] * rows,
            "lum": [1] * rows,
            "atm": [1] * rows,
            "surf": [1] * rows,
            "manv": [1, 2] * 5,
            "secu1": [1] * rows,
            "secu2": [0] * rows,
            "secu3": [0] * rows,
            "agg": [1] * rows,
            "catr": [3] * rows,
            "catu": [1] * rows,
        }
    )


def test_feature_transform_is_deterministic_with_stable_output_names() -> None:
    source = prepared_rows()
    transformer = AccidentFeatureTransformer(geo_bins=4, rare_threshold=0)

    transformer.fit(source)
    first = transformer.transform(source)
    second = transformer.transform(source)

    pd.testing.assert_frame_equal(first, second)
    assert first.columns.tolist() == transformer.get_feature_names_out().tolist()
    assert {"Num_Acc", "accident_date", "lat", "long"}.isdisjoint(first.columns)


def test_feature_state_is_learned_only_from_fit_data() -> None:
    train = prepared_rows()
    future = train.iloc[[0]].copy()
    future["lat"] = 50.0
    future["long"] = 8.0
    future["agg"] = 99
    transformer = AccidentFeatureTransformer(geo_bins=4, rare_threshold=0).fit(train)

    transformed = transformer.transform(future)

    assert transformer.lat_edges_[-1] < 50.0
    assert transformer.long_edges_[-1] < 8.0
    assert pd.isna(transformed.iloc[0]["lat_bin"])
    assert transformed.iloc[0]["agg_catv_group"] == -1


def test_unknown_modalities_are_supported_without_changing_feature_schema() -> None:
    train = prepared_rows()
    unknown = train.iloc[[0]].copy()
    unknown["catr"] = 999
    transformer = AccidentFeatureTransformer(rare_threshold=0).fit(train)

    transformed = transformer.transform(unknown)

    assert transformed.columns.tolist() == transformer.get_feature_names_out().tolist()
    assert transformed.iloc[0]["catv_group_x_catr"] == -1


def test_missing_input_columns_are_rejected() -> None:
    with pytest.raises(ValueError, match="Colonnes préparées manquantes"):
        AccidentFeatureTransformer().fit(prepared_rows().drop(columns=["lat"]))
