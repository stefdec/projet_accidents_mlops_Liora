"""Sklearn-compatible feature engineering learned only from fitted data."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted

DAY_PERIOD_MAPPING = {"matin": 1, "apres_midi": 2, "soir": 3, "nuit": 4}
DAY_OF_WEEK_MAPPING = {
    "Monday": 1,
    "Tuesday": 2,
    "Wednesday": 3,
    "Thursday": 4,
    "Friday": 5,
    "Saturday": 6,
    "Sunday": 7,
}
CATV_GROUP_MAPPING = {
    "Véhicules légers": 0,
    "Deux-roues motorisés": 1,
    "Mobilités douces / individuelles": 2,
    "Utilitaires": 3,
    "Poids lourds / marchandises": 4,
    "Transport collectif": 5,
    "Autres / indéterminés": 6,
    "Véhicules spéciaux / agricoles": 7,
    "Rail / tramway": 8,
}
VALUE_MAPPINGS = {
    "macro_choc": {
        "Aucun": 0,
        "Frontal": 1,
        "Arriere": 2,
        "Lateral": 3,
        "Multiple": 4,
        "Inconnu": 5,
    },
    "presence_obstacle_fixe": {"Non/Inconnu": 0, "Oui": 1},
    "macro_obsm": {
        "Aucun": 0,
        "Vehicule": 1,
        "Pieton": 2,
        "Animal": 3,
        "Autre/Inconnu": 4,
    },
    "type_crash": {
        "Vehicule_vs_Vehicule": 0,
        "Vehicule_vs_Pieton": 1,
        "Seul_contre_Obstacle_Fixe": 2,
        "Autre/Multiple": 3,
    },
}
INTERACTION_COLS = [
    "catv_group_x_catr",
    "veh_manv",
    "surf_vma",
    "lum_atm",
    "secu1_catv",
    "secu2_catv",
    "secu3_catv",
    "age_vma",
    "agg_catv_group",
]
HIGH_CARDINALITY_COLS = {"lat_bin", "long_bin", "score_conditions_dangereuses"}
NUMERIC_COLS = {"age", "nb_victimes_accident"}
TEXT_OUTPUT_COLS = {"age_group", "age_group_x_catv_group"}
METADATA_COLS = {"Num_Acc", "accident_date"}
REQUIRED_INPUT_COLS = {
    "age",
    "agg",
    "atm",
    "catr",
    "catu",
    "catv_group",
    "day_of_week",
    "day_period",
    "lat",
    "long",
    "lum",
    "macro_choc",
    "macro_obsm",
    "manv",
    "month",
    "presence_obstacle_fixe",
    "secu1",
    "secu2",
    "secu3",
    "surf",
    "type_crash",
    "vma",
    "year",
}


class AccidentFeatureTransformer(TransformerMixin, BaseEstimator):
    """Build stable model features without learning from validation data."""

    def __init__(
        self,
        *,
        geo_bins: int = 1000,
        rare_threshold: float = 0.005,
        interaction_rare_threshold: float = 0.001,
    ) -> None:
        self.geo_bins = geo_bins
        self.rare_threshold = rare_threshold
        self.interaction_rare_threshold = interaction_rare_threshold

    def fit(self, X: pd.DataFrame, y: object = None) -> AccidentFeatureTransformer:
        del y
        raw = self._validate_input(X)
        self.n_features_in_ = raw.shape[1]
        self.feature_names_in_ = np.asarray(raw.columns, dtype=object)
        self.lat_edges_ = self._learn_bin_edges(raw["lat"], "lat")
        self.long_edges_ = self._learn_bin_edges(raw["long"], "long")
        transformed = self._apply_geographic_bins(self._build_features(raw))
        self.interaction_mappings_ = {
            column: {
                value: code
                for code, value in enumerate(
                    sorted(self._modalities(transformed[column]).unique().tolist())
                )
            }
            for column in INTERACTION_COLS
        }
        transformed = self._apply_interaction_mappings(transformed)
        transformed = transformed.drop(columns=list(METADATA_COLS), errors="ignore")
        self.rare_modalities_ = {}
        for column in transformed.columns:
            if column in HIGH_CARDINALITY_COLS or column in NUMERIC_COLS:
                continue
            threshold = (
                self.interaction_rare_threshold
                if column in INTERACTION_COLS
                else self.rare_threshold
            )
            frequencies = transformed[column].value_counts(normalize=True, dropna=False)
            self.rare_modalities_[column] = frequencies[
                frequencies < threshold
            ].index.tolist()
        self.output_features_ = np.asarray(transformed.columns, dtype=object)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        check_is_fitted(
            self,
            [
                "lat_edges_",
                "long_edges_",
                "interaction_mappings_",
                "rare_modalities_",
                "output_features_",
            ],
        )
        transformed = self._apply_geographic_bins(
            self._build_features(self._validate_input(X))
        )
        transformed = self._apply_interaction_mappings(transformed)
        transformed = transformed.drop(columns=list(METADATA_COLS), errors="ignore")
        for column, rare_values in self.rare_modalities_.items():
            if rare_values:
                transformed[column] = (
                    transformed[column]
                    .astype("object")
                    .where(~transformed[column].isin(rare_values), -1)
                )
        missing = sorted(set(self.output_features_).difference(transformed.columns))
        if missing:
            raise ValueError(f"Features produites manquantes : {missing}")
        transformed = transformed[list(self.output_features_)].copy()
        for column in transformed.columns:
            if column in TEXT_OUTPUT_COLS:
                transformed[column] = (
                    transformed[column].astype("string").fillna("__MISSING__")
                )
            else:
                transformed[column] = pd.to_numeric(
                    transformed[column], errors="coerce"
                )
        return transformed

    def get_feature_names_out(self, input_features: object = None) -> np.ndarray:
        del input_features
        check_is_fitted(self, "output_features_")
        return self.output_features_.copy()

    @staticmethod
    def _modalities(series: pd.Series) -> pd.Series:
        return series.astype("string").fillna("__MISSING__")

    def _validate_input(self, X: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(X, pd.DataFrame):
            raise TypeError("AccidentFeatureTransformer attend un DataFrame pandas")
        missing = sorted(REQUIRED_INPUT_COLS.difference(X.columns))
        if missing:
            raise ValueError(f"Colonnes préparées manquantes : {missing}")
        return X.copy()

    def _learn_bin_edges(self, series: pd.Series, column: str) -> np.ndarray:
        values = pd.to_numeric(series, errors="coerce").dropna()
        if values.empty:
            raise ValueError(f"Impossible d'apprendre les bornes de {column}")
        _, edges = pd.cut(
            values, bins=self.geo_bins, labels=False, retbins=True, duplicates="drop"
        )
        return np.asarray(edges, dtype=float)

    def _apply_geographic_bins(self, frame: pd.DataFrame) -> pd.DataFrame:
        result = frame.copy()
        result["lat_bin"] = pd.cut(
            pd.to_numeric(result["lat"], errors="coerce"),
            bins=self.lat_edges_,
            labels=False,
            include_lowest=True,
        )
        result["long_bin"] = pd.cut(
            pd.to_numeric(result["long"], errors="coerce"),
            bins=self.long_edges_,
            labels=False,
            include_lowest=True,
        )
        return result.drop(columns=["lat", "long"])

    def _apply_interaction_mappings(self, frame: pd.DataFrame) -> pd.DataFrame:
        result = frame.copy()
        for column, mapping in self.interaction_mappings_.items():
            result[column] = (
                self._modalities(result[column]).map(mapping).fillna(-1).astype(int)
            )
        return result

    @staticmethod
    def _build_features(X: pd.DataFrame) -> pd.DataFrame:
        frame = X.copy()
        frame["day_period"] = frame["day_period"].map(DAY_PERIOD_MAPPING)
        frame["day_of_week"] = frame["day_of_week"].map(DAY_OF_WEEK_MAPPING)
        for column, mapping in VALUE_MAPPINGS.items():
            frame[column] = frame[column].map(mapping)
        frame["catv_group"] = frame["catv_group"].map(CATV_GROUP_MAPPING)
        frame["vma_categorie"] = pd.cut(
            frame["vma"],
            bins=[0, 30, 50, 80, 90, 110, 130, np.inf],
            labels=[0, 1, 2, 3, 4, 5, 6],
        )
        frame = frame.drop(columns=["vma"])
        year_month = pd.to_datetime(
            {"year": frame["year"], "month": frame["month"], "day": 1}, errors="coerce"
        )
        frame["is_covid"] = year_month.between("2020-03-01", "2021-12-01").astype(int)
        for column, left, right in (
            ("lum_atm", "lum", "atm"),
            ("surf_vma", "surf", "vma_categorie"),
            ("veh_manv", "catv_group", "manv"),
            ("secu1_catv", "catv_group", "secu1"),
            ("secu2_catv", "catv_group", "secu2"),
            ("secu3_catv", "catv_group", "secu3"),
            ("agg_catv_group", "catv_group", "agg"),
            ("age_vma", "age", "vma_categorie"),
        ):
            frame[column] = frame[left].astype(str) + "_" + frame[right].astype(str)
        frame["score_conditions_dangereuses"] = (
            frame["lum"].isin([3, 4]).astype(int)
            + frame["atm"].isin([2, 3, 4, 5, 6]).astype(int)
            + (~frame["surf"].isin([2, 4, 5, 7])).astype(int)
            + frame["vma_categorie"].isin([4, 5, 6]).astype(int)
            + frame["day_period"].eq(4).astype(int)
        )
        frame["age_group"] = pd.cut(
            frame["age"],
            bins=[0, 18, 25, 40, 60, 75, 120],
            labels=["0-18", "18-25", "25-40", "40-60", "60-75", "75+"],
            include_lowest=True,
        )
        frame["age_group_x_catv_group"] = (
            frame["age_group"].astype(str) + "_" + frame["catv_group"].astype(str)
        )
        frame["is_vulnerable_user"] = (
            frame["catu"].eq(3) | frame["catv_group"].isin([1, 2])
        ).astype(int)
        frame["catv_group_x_catr"] = (
            frame["catv_group"].astype(str) + "_" + frame["catr"].astype(str)
        )
        if "nb_victimes_accident" not in frame:
            frame["nb_victimes_accident"] = frame.groupby("Num_Acc", dropna=False)[
                "Num_Acc"
            ].transform("size")
        safety_columns = ["secu1", "secu2", "secu3"]
        frame["has_seatbelt"] = frame[safety_columns].isin([1]).any(axis=1).astype(int)
        frame["has_helmet"] = frame[safety_columns].isin([2]).any(axis=1).astype(int)
        frame["has_gloves"] = frame[safety_columns].isin([6, 7]).any(axis=1).astype(int)
        frame["has_unknown_safety"] = (
            frame[safety_columns].isin([8]).any(axis=1).astype(int)
        )
        frame["has_no_safety"] = (
            ~frame[safety_columns].isin([1, 2, 3, 4, 5, 6, 7]).any(axis=1)
        ).astype(int)
        return frame
