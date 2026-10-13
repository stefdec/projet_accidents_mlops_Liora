"""
01_clean.py
===========
Point de départ :
    data/raw/accidents_2017_2024.csv

Ce script reprend uniquement les transformations réellement effectuées
dans LGBM_pipeline.ipynb APRÈS la fusion des fichiers annuels.

Sortie :
    data/processed/accidents_2019_2024_cleaned.csv
"""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "accidents_2017_2024.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "accidents_2019_2024_cleaned.csv"


COLUMNS_TO_DROP = [
    "v2",
    "lartpc",
    "gps",
    "env1",
    "occutc",
    "id_vehicule_y",
    "id_usager",
    "v1",
    "nbv",
    "pr",
    "pr1",
]


def coord_to_old_format(value):
    """
    Reproduit l'harmonisation du notebook :
    - degrés décimaux -> entier x100000
    - ancien format (>180 en valeur absolue) -> conservé.
    """
    if pd.isna(value):
        return pd.NA

    value = str(value).replace(",", ".")

    try:
        value = float(value)
    except (TypeError, ValueError):
        return pd.NA

    if abs(value) > 180:
        return int(round(value))

    return int(round(value * 100000))


def format_heure(value):
    """Transforme par exemple 930 -> 09:30."""
    value = str(value).strip()

    if ":" in value:
        return value

    value = value.zfill(4)
    return value[:-2] + ":" + value[-2:]


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Doublons exacts
    df = df.drop_duplicates(keep="first")

    # Colonnes supprimées dans le notebook
    df = df.drop(columns=COLUMNS_TO_DROP, errors="ignore")

    # actp : A/B -> 10/11
    if "actp" in df.columns:
        df["actp"] = df["actp"].replace({
            "A": "10",
            "B": "11",
        })
        df["actp"] = pd.to_numeric(
            df["actp"],
            errors="coerce",
        ).astype("Int64")

    # Harmonisation latitude / longitude
    for col in ["lat", "long"]:
        if col in df.columns:
            df[col] = df[col].apply(coord_to_old_format)

    # Conversion numérique
    for col in ["larrout", "lat", "long"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            ).astype("Float32")

    # 17 -> 2017, 18 -> 2018
    if "an" in df.columns:
        df["an"] = pd.to_numeric(df["an"], errors="coerce")
        df["an"] = df["an"].apply(
            lambda x: x + 2000 if pd.notna(x) and x < 100 else x
        )

    # Harmonisation heure
    if "hrmn" in df.columns:
        df["hrmn"] = df["hrmn"].apply(format_heure)

    # Création de la date complète
    required = {"an", "mois", "jour", "hrmn"}

    if required.issubset(df.columns):
        date_str = (
            df["an"].astype("Int64").astype(str)
            + "-"
            + pd.to_numeric(df["mois"], errors="coerce")
                .astype("Int64").astype(str).str.zfill(2)
            + "-"
            + pd.to_numeric(df["jour"], errors="coerce")
                .astype("Int64").astype(str).str.zfill(2)
            + " "
            + df["hrmn"].astype(str)
        )

        df["date"] = pd.to_datetime(
            date_str,
            format="%Y-%m-%d %H:%M",
            errors="coerce",
        )

    # Ancienne colonne technique
    df = df.drop(columns=["id_vehicule_x"], errors="ignore")

    # Le modèle historique final utilise 2019-2024
    if "year" not in df.columns:
        raise ValueError("La colonne 'year' est absente du dataset.")

    df = df[
        ~df["year"].isin([2017, 2018])
    ].copy()

    return df


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {INPUT_FILE}\n"
            "Place accidents_2017_2024.csv dans data/raw/."
        )

    df = pd.read_csv(
        INPUT_FILE,
        encoding="latin1",
        low_memory=False,
    )

    print("[01 CLEAN] entrée :", df.shape)

    df = clean_dataset(df)

    df.to_csv(OUTPUT_FILE, index=False)

    print("[01 CLEAN] sortie :", df.shape)
    print("[01 CLEAN] fichier :", OUTPUT_FILE)
    print("[01 CLEAN] années :", sorted(df["year"].dropna().unique()))


if __name__ == "__main__":
    main()
