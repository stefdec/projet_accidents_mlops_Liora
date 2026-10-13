"""Construit l'entrée supervisée sans apprendre sur les données.

Toutes les transformations qui apprennent une distribution (bornes
géographiques, mappings, modalités rares et target encoding) vivent désormais
dans ``AccidentFeatureTransformer`` et sont ajustées après le split temporel.
"""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "accidents_2019_2024_prepared.csv"
)
OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "features"
    / "data_final_binaire.csv"
)


def build_model_input(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute uniquement la cible binaire, sans état appris."""
    if "grav" not in df.columns:
        raise ValueError("La colonne cible grav est absente")
    if "accident_date" not in df.columns:
        raise ValueError("La métadonnée accident_date est absente")

    result = df.copy()
    result["grav_binaire"] = result["grav"].isin([2, 3]).astype(int)
    return result.drop(columns=["grav"])


def main() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    df = pd.read_csv(INPUT_FILE, low_memory=False)
    print("[03 FEATURES] entrée :", df.shape)

    model_input = build_model_input(df)
    model_input.to_csv(OUTPUT_FILE, index=False)

    print("[03 FEATURES] sortie :", model_input.shape)
    print("[03 FEATURES] transformations apprises : aucune")
    print("[03 FEATURES] dataset :", OUTPUT_FILE)


if __name__ == "__main__":
    main()
