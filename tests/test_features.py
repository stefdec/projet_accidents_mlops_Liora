import pandas as pd

from projet_accidents_mlops.features import AccidentFeatureTransformer


def _prepared_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Num_Acc": list(range(1, 11)),
            "year": [2023] * 10,
            "month": [1] * 10,
            "mois": [1] * 10,
            "day_of_week": ["Monday"] * 10,
            "day_period": ["matin"] * 10,
            "age": [20, 22, 30, 35, 45, 50, 65, 70, 80, 25],
            "catv_group": ["Véhicules légers"] * 10,
            "macro_choc": ["Frontal"] * 10,
            "macro_obsm": ["Vehicule"] * 10,
            "type_crash": ["Vehicule_vs_Vehicule"] * 10,
            "presence_obstacle_fixe": ["Non/Inconnu"] * 10,
            "lat": [43.0, 43.1, 43.2, 43.3, 43.4, 43.5, 43.6, 43.7, 43.8, 43.9],
            "long": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9],
            "vma": [50] * 10,
            "lum": [1] * 10,
            "atm": [1] * 10,
            "surf": [1] * 10,
            "manv": [1] * 10,
            "secu1": [1] * 10,
            "secu2": [0] * 10,
            "secu3": [0] * 10,
            "agg": [1] * 10,
            "catr": [3] * 10,
            "catu": [1] * 10,
        }
    )


def test_feature_state_is_learned_only_from_training_rows() -> None:
    train = _prepared_rows()
    future = train.iloc[[0]].copy()
    future["Num_Acc"] = 99
    future["lat"] = 50.0
    future["long"] = 8.0
    future["agg"] = 99

    transformer = AccidentFeatureTransformer(geo_bins=4).fit(train)
    transformed_future = transformer.transform(future)

    assert transformer.lat_edges_[-1] < 50.0
    assert transformer.long_edges_[-1] < 8.0
    assert pd.isna(transformed_future.iloc[0]["lat_bin"])
    assert pd.isna(transformed_future.iloc[0]["long_bin"])
    assert transformed_future.iloc[0]["agg_catv_group"] == -1


def test_feature_transformer_removes_metadata_and_keeps_stable_columns() -> None:
    train = _prepared_rows()
    transformer = AccidentFeatureTransformer(geo_bins=4).fit(train)

    transformed = transformer.transform(train)

    assert transformed.shape[0] == train.shape[0]
    assert transformed.columns.tolist() == transformer.get_feature_names_out().tolist()
    assert "Num_Acc" not in transformed.columns
    assert "accident_date" not in transformed.columns
    assert "lat" not in transformed.columns
    assert "long" not in transformed.columns
