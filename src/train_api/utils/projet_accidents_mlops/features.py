"""Feature engineering sklearn appris uniquement sur les données passées."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted


DAY_PERIOD_MAPPING = {
    "matin": 1,
    "apres_midi": 2,
    "soir": 3,
    "nuit": 4,
}

DAY_OF_WEEK_MAPPING = {
    "Monday": 1,
    "Tuesday": 2,
    "Wednesday": 3,
    "Thursday": 4,
    "Friday": 5,
    "Saturday": 6,
    "Sunday": 7,
}

MACRO_CHOC_MAPPING = {
    "Aucun": 0,
    "Frontal": 1,
    "Arriere": 2,
    "Lateral": 3,
    "Multiple": 4,
    "Inconnu": 5,
}

OBSTACLE_FIXE_MAPPING = {
    "Non/Inconnu": 0,
    "Oui": 1,
}

MACRO_OBSM_MAPPING = {
    "Aucun": 0,
    "Vehicule": 1,
    "Pieton": 2,
    "Animal": 3,
    "Autre/Inconnu": 4,
}

TYPE_CRASH_MAPPING = {
    "Vehicule_vs_Vehicule": 0,
    "Vehicule_vs_Pieton": 1,
    "Seul_contre_Obstacle_Fixe": 2,
    "Autre/Multiple": 3,
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

INTERACTION_COLS = [
    "catv_group_x_catr",
    "veh_manv",
    "surf_vma",
    "lum_atm",
    "secu1_catv",
    "secu2_catv",
    "age_vma",
    "secu3_catv",
    "agg_catv_group",
]

HIGH_CARDINALITY_COLS = {
    "lat_bin",
    "long_bin",
    "score_conditions_dangereuses",
}

NUMERIC_COLS = {
    "age",
    "nb_victimes_accident",
}

TEXT_OUTPUT_COLS = {
    "age_group",
    "age_group_x_catv_group",
}

METADATA_COLS = {
    "Num_Acc",
    "accident_date",
}

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
    """Reproduit les features historiques sans regarder validation ou test.

    ``fit`` apprend les bornes géographiques, les codes d'interaction et les
    modalités rares sur le seul jeu reçu. ``transform`` réutilise cet état et
    affecte ``-1`` aux interactions inconnues.
    """

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

    def fit(self, X: pd.DataFrame, y=None):
        raw = self._validate_input(X)
        self.n_features_in_ = raw.shape[1]
        self.feature_names_in_ = np.asarray(raw.columns, dtype=object)

        self.lat_edges_ = self._learn_bin_edges(raw["lat"], "lat")
        self.long_edges_ = self._learn_bin_edges(raw["long"], "long")

        transformed = self._build_deterministic_features(raw)
        transformed = self._apply_geographic_bins(transformed)

        self.interaction_mappings_ = {}
        for col in INTERACTION_COLS:
            modalities = sorted(
                self._normalise_modalities(transformed[col]).unique().tolist()
            )
            self.interaction_mappings_[col] = {
                modality: code for code, modality in enumerate(modalities)
            }

        transformed = self._apply_interaction_mappings(transformed)
        transformed = transformed.drop(columns=list(METADATA_COLS), errors="ignore")

        self.rare_modalities_ = {}
        for col in transformed.columns:
            if col in HIGH_CARDINALITY_COLS or col in NUMERIC_COLS:
                continue

            threshold = (
                self.interaction_rare_threshold
                if col in INTERACTION_COLS
                else self.rare_threshold
            )
            frequencies = transformed[col].value_counts(
                normalize=True,
                dropna=False,
            )
            self.rare_modalities_[col] = frequencies[
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
        transformed = self._build_deterministic_features(
            self._validate_input(X)
        )
        transformed = self._apply_geographic_bins(transformed)
        transformed = self._apply_interaction_mappings(transformed)
        transformed = transformed.drop(columns=list(METADATA_COLS), errors="ignore")
        transformed = self._apply_rare_modalities(transformed)

        missing = [
            col for col in self.output_features_ if col not in transformed.columns
        ]
        if missing:
            raise ValueError(f"Features produites manquantes : {missing}")

        transformed = transformed[list(self.output_features_)].copy()
        for col in transformed.columns:
            if col in TEXT_OUTPUT_COLS:
                transformed[col] = (
                    transformed[col].astype("string").fillna("__MISSING__")
                )
            else:
                transformed[col] = pd.to_numeric(
                    transformed[col],
                    errors="coerce",
                )

        return transformed

    def get_feature_names_out(self, input_features=None) -> np.ndarray:
        check_is_fitted(self, "output_features_")
        return self.output_features_.copy()

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
            values,
            bins=self.geo_bins,
            labels=False,
            retbins=True,
            duplicates="drop",
        )
        return np.asarray(edges, dtype=float)

    @staticmethod
    def _normalise_modalities(series: pd.Series) -> pd.Series:
        return series.astype("string").fillna("__MISSING__")

    def _apply_geographic_bins(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["lat_bin"] = pd.cut(
            pd.to_numeric(df["lat"], errors="coerce"),
            bins=self.lat_edges_,
            labels=False,
            include_lowest=True,
        )
        df["long_bin"] = pd.cut(
            pd.to_numeric(df["long"], errors="coerce"),
            bins=self.long_edges_,
            labels=False,
            include_lowest=True,
        )
        return df.drop(columns=["lat", "long"])

    def _apply_interaction_mappings(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col, mapping in self.interaction_mappings_.items():
            df[col] = (
                self._normalise_modalities(df[col])
                .map(mapping)
                .fillna(-1)
                .astype(int)
            )
        return df

    def _apply_rare_modalities(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col, rare_values in self.rare_modalities_.items():
            if col not in df.columns or not rare_values:
                continue
            values = df[col].astype("object")
            df[col] = values.where(~values.isin(rare_values), -1)
        return df

    @staticmethod
    def _build_deterministic_features(X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()

        df["day_period"] = df["day_period"].map(DAY_PERIOD_MAPPING)
        df["day_of_week"] = df["day_of_week"].map(DAY_OF_WEEK_MAPPING)
        df["macro_choc"] = df["macro_choc"].map(MACRO_CHOC_MAPPING)
        df["presence_obstacle_fixe"] = df["presence_obstacle_fixe"].map(
            OBSTACLE_FIXE_MAPPING
        )
        df["macro_obsm"] = df["macro_obsm"].map(MACRO_OBSM_MAPPING)
        df["type_crash"] = df["type_crash"].map(TYPE_CRASH_MAPPING)
        df["catv_group"] = df["catv_group"].map(CATV_GROUP_MAPPING)

        df["vma_categorie"] = pd.cut(
            df["vma"],
            bins=[0, 30, 50, 80, 90, 110, 130, np.inf],
            labels=[0, 1, 2, 3, 4, 5, 6],
        )
        df = df.drop(columns=["vma"])

        year_month = pd.to_datetime(
            {"year": df["year"], "month": df["month"], "day": 1},
            errors="coerce",
        )
        df["is_covid"] = year_month.between(
            "2020-03-01", "2021-12-01"
        ).astype(int)

        df["lum_atm"] = df["lum"].astype(str) + "_" + df["atm"].astype(str)
        df["surf_vma"] = (
            df["surf"].astype(str)
            + "_"
            + df["vma_categorie"].astype(str)
        )
        df["veh_manv"] = (
            df["catv_group"].astype(str) + "_" + df["manv"].astype(str)
        )
        df["secu1_catv"] = (
            df["catv_group"].astype(str) + "_" + df["secu1"].astype(str)
        )
        df["secu2_catv"] = (
            df["catv_group"].astype(str) + "_" + df["secu2"].astype(str)
        )
        df["secu3_catv"] = (
            df["catv_group"].astype(str) + "_" + df["secu3"].astype(str)
        )
        df["agg_catv_group"] = (
            df["catv_group"].astype(str) + "_" + df["agg"].astype(str)
        )
        df["age_vma"] = (
            df["age"].astype(str)
            + "_"
            + df["vma_categorie"].astype(str)
        )

        df["score_conditions_dangereuses"] = (
            df["lum"].isin([3, 4]).astype(int)
            + df["atm"].isin([2, 3, 4, 5, 6]).astype(int)
            + (~df["surf"].isin([2, 4, 5, 7])).astype(int)
            + df["vma_categorie"].isin([4, 5, 6]).astype(int)
            + df["day_period"].eq(4).astype(int)
        )

        df["age_group"] = pd.cut(
            df["age"],
            bins=[0, 18, 25, 40, 60, 75, 120],
            labels=["0-18", "18-25", "25-40", "40-60", "60-75", "75+"],
            include_lowest=True,
        )
        df["age_group_x_catv_group"] = (
            df["age_group"].astype(str)
            + "_"
            + df["catv_group"].astype(str)
        )

        df["is_vulnerable_user"] = (
            df["catu"].eq(3) | df["catv_group"].isin([1, 2])
        ).astype(int)
        df["catv_group_x_catr"] = (
            df["catv_group"].astype(str) + "_" + df["catr"].astype(str)
        )

        if "nb_victimes_accident" not in df.columns:
            if "Num_Acc" in df.columns:
                df["nb_victimes_accident"] = df.groupby(
                    "Num_Acc", dropna=False
                )["Num_Acc"].transform("size")
            else:
                df["nb_victimes_accident"] = 1

        secu_cols = ["secu1", "secu2", "secu3"]
        df["has_seatbelt"] = df[secu_cols].isin([1]).any(axis=1).astype(int)
        df["has_helmet"] = df[secu_cols].isin([2]).any(axis=1).astype(int)
        df["has_gloves"] = df[secu_cols].isin([6, 7]).any(axis=1).astype(int)
        df["has_unknown_safety"] = (
            df[secu_cols].isin([8]).any(axis=1).astype(int)
        )
        df["has_no_safety"] = (
            ~df[secu_cols].isin([1, 2, 3, 4, 5, 6, 7]).any(axis=1)
        ).astype(int)

        return df
