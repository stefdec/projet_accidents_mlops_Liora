"""
02_prepare.py
=============
Reproduction locale de pipeline_transfo_clean.ipynb.

Entrée :
    data/processed/accidents_2019_2024_cleaned.csv

Sortie :
    data/processed/accidents_2019_2024_prepared.csv

Cette étape crée les variables métier utilisées ensuite par le feature
engineering LightGBM.
"""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "accidents_2019_2024_cleaned.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "accidents_2019_2024_prepared.csv"
)


GRAVITY_MAPPING = {
    1.0: 0.0,
    4.0: 1.0,
    3.0: 2.0,
    2.0: 3.0,
}

DAY_PERIOD_BINS = [0, 6, 12, 18, 24]
DAY_PERIOD_LABELS = [
    "nuit",
    "matin",
    "apres_midi",
    "soir",
]

COLUMNS_TO_DROP = [
    "secu",
    "num_veh",
    "senc",
    "occutc",
    "voie",
    "nbv",
    "plan",
    "lartpc",
    "larrout",
    "an",
    "jour",
    "hrmn",
    "int",
    "com",
    "adr",
    "dep",
    "an_nais",
    "date",
    "catv",
    "obsm",
    "obs",
    "choc",
]

MINUS_ONE_IS_NAN = [
    "place",
    "sexe",
    "trajet",
    "locp",
    "actp",
    "etatp",
    "manv",
    "circ",
    "vosp",
    "prof",
    "surf",
    "infra",
    "situ",
    "lum",
    "atm",
    "col",
    "secu1",
    "secu2",
    "secu3",
    "motor",
]

ZERO_IS_NAN = [
    "trajet",
    "locp",
    "actp",
    "manv",
    "motor",
    "secu1",
    "secu2",
    "secu3",
    "vma",
]


def recode_gravity(df):
    df = df.copy()

    if "grav" not in df.columns:
        return df

    df = df[df["grav"] != -1]

    df["grav"] = (
        pd.to_numeric(df["grav"], errors="coerce")
        .map(GRAVITY_MAPPING)
    )

    df = df.dropna(subset=["grav"])

    return df


def add_temporal_features(df):
    df = df.copy()

    accident_dates = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    invalid_date_count = int(accident_dates.isna().sum())
    if invalid_date_count:
        raise ValueError(
            "Des dates d'accident sont invalides : "
            f"{invalid_date_count} ligne(s)."
        )

    # Métadonnée conservée pour les découpages temporels. Elle ne doit pas
    # être utilisée comme variable explicative par le modèle.
    df["accident_date"] = accident_dates.dt.normalize()
    df["month"] = accident_dates.dt.month
    df["day_of_week"] = accident_dates.dt.day_name()
    df["hour"] = accident_dates.dt.hour

    df["day_period"] = pd.cut(
        df["hour"],
        bins=DAY_PERIOD_BINS,
        labels=DAY_PERIOD_LABELS,
        right=False,
    )

    return df


def add_age(df):
    df = df.copy()

    accident_year = pd.to_datetime(
        df["date"],
        errors="coerce",
    ).dt.year

    df["age"] = accident_year - df["an_nais"]

    df.loc[
        (df["age"] < 0) | (df["age"] > 110),
        "age",
    ] = np.nan

    # Reproduction exacte du notebook :
    # suppression des lignes sans âge
    df = df.dropna(
        axis=0,
        subset=["age"],
    )

    return df


def clean_infrastructure_features(df):
    df = df.copy()

    for col in ["catr", "circ", "vma", "motor", "catv"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

    if "vma" in df.columns:
        df.loc[
            (df["vma"] < 0) | (df["vma"] > 130),
            "vma",
        ] = np.nan

    return df


def group_vehicle_category(catv):
    if pd.isna(catv):
        return "Non renseigné"

    catv = int(catv)

    if catv in [7, 8, 9]:
        return "Véhicules légers"

    if catv in [
        2, 4, 5, 6,
        30, 31, 32, 33, 34,
        41, 42, 43,
    ]:
        return "Deux-roues motorisés"

    if catv in [1, 50, 60, 80]:
        return "Mobilités douces / individuelles"

    if catv in [10, 11, 12]:
        return "Utilitaires"

    if catv in [13, 14, 15, 16, 17]:
        return "Poids lourds / marchandises"

    if catv in [18, 37, 38]:
        return "Transport collectif"

    if catv in [20, 21]:
        return "Véhicules spéciaux / agricoles"

    if catv in [19, 39, 40]:
        return "Rail / tramway"

    return "Autres / indéterminés"


def add_vehicle_group(df):
    df = df.copy()
    df["catv_group"] = df["catv"].apply(group_vehicle_category)
    return df


def add_crash_features(df):
    df = df.copy()

    for col in ["col", "choc", "obs", "obsm"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

    choc_conditions = [
        df["choc"].isin([1, 2, 3]),
        df["choc"].isin([4, 5, 6]),
        df["choc"].isin([7, 8]),
        df["choc"] == 9,
        df["choc"] == 0,
    ]

    df["macro_choc"] = np.select(
        choc_conditions,
        [
            "Frontal",
            "Arriere",
            "Lateral",
            "Multiple",
            "Aucun",
        ],
        default="Inconnu",
    )

    df["presence_obstacle_fixe"] = np.where(
        df["obs"].isin(range(1, 18)),
        "Oui",
        "Non/Inconnu",
    )

    obsm_conditions = [
        df["obsm"] == 1,
        df["obsm"].isin([2, 4]),
        df["obsm"].isin([5, 6]),
        df["obsm"] == 0,
    ]

    df["macro_obsm"] = np.select(
        obsm_conditions,
        [
            "Pieton",
            "Vehicule",
            "Animal",
            "Aucun",
        ],
        default="Autre/Inconnu",
    )

    crash_conditions = [
        (
            (df["presence_obstacle_fixe"] == "Oui")
            & (df["macro_obsm"] == "Aucun")
        ),
        df["macro_obsm"] == "Vehicule",
        df["macro_obsm"] == "Pieton",
    ]

    df["type_crash"] = np.select(
        crash_conditions,
        [
            "Seul_contre_Obstacle_Fixe",
            "Vehicule_vs_Vehicule",
            "Vehicule_vs_Pieton",
        ],
        default="Autre/Multiple",
    )

    return df.drop(
        columns=["choc", "obs", "obsm"],
        errors="ignore",
    )


def drop_unused_columns(df):
    existing = [
        col for col in COLUMNS_TO_DROP
        if col in df.columns
    ]

    return df.drop(
        columns=existing,
        errors="ignore",
    )


def replace_minus_one_with_nan(df, columns):
    df = df.copy()

    for col in columns:
        if col in df.columns:
            df[col] = df[col].replace(-1, np.nan)

    return df


def replace_zero_with_nan(df, columns):
    df = df.copy()

    for col in columns:
        if col in df.columns:
            df[col] = df[col].replace(0, np.nan)

    return df


def clean_nan(df):
    df = df.copy()

    fill_zero = [
        "etatp",
        "locp",
        "actp",
        "vosp",
        "secu1",
        "secu2",
        "secu3",
        "trajet",
        "motor",
        "manv",
        "circ",
        "infra",
    ]

    required_not_nan = [
        "col",
        "place",
        "vma",
        "lum",
        "atm",
        "sexe",
        "prof",
        "surf",
        "situ",
    ]

    for col in fill_zero:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    df = df.dropna(
        subset=[
            col for col in required_not_nan
            if col in df.columns
        ]
    )

    return df


def prepare_dataset(df):
    df = recode_gravity(df)
    df = add_temporal_features(df)
    df = add_age(df)
    df = clean_infrastructure_features(df)
    df = add_vehicle_group(df)
    df = add_crash_features(df)
    df = drop_unused_columns(df)
    df = replace_zero_with_nan(df, ZERO_IS_NAN)
    df = replace_minus_one_with_nan(df, MINUS_ONE_IS_NAN)
    df = clean_nan(df)

    return df


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    df = pd.read_csv(
        INPUT_FILE,
        low_memory=False,
    )

    print("[02 PREPARE] entrée :", df.shape)

    df = prepare_dataset(df)

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("[02 PREPARE] sortie :", df.shape)
    print("[02 PREPARE] fichier :", OUTPUT_FILE)


if __name__ == "__main__":
    main()
