"""Assemble le dataset historique et les Parquet hebdomadaires disponibles."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from projet_accidents_mlops.weekly_data import build_snapshot_from_weekly_parquets


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_INPUT = PROJECT_ROOT / "data" / "features" / "data_final_binaire.csv"
INCOMING_DIR = PROJECT_ROOT / "data" / "incoming"
OUTPUT_FILE = PROJECT_ROOT / "data" / "features" / "training_snapshot.csv"
MANIFEST_FILE = PROJECT_ROOT / "reports" / "snapshot_manifest.json"
PARAMS_FILE = PROJECT_ROOT / "params.yaml"


def main() -> None:
    params = yaml.safe_load(PARAMS_FILE.read_text(encoding="utf-8"))["retraining"]
    base_df = pd.read_csv(BASE_INPUT, low_memory=False)
    snapshot = build_snapshot_from_weekly_parquets(
        base_df,
        INCOMING_DIR,
        int(params["weeks_2024"]),
        manifest_source=INCOMING_DIR.relative_to(PROJECT_ROOT).as_posix(),
        history_start=params["history_start"],
        start_2024=params["start_2024"],
        end_2024=params["end_2024"],
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    snapshot.data.to_csv(OUTPUT_FILE, index=False)
    MANIFEST_FILE.write_text(
        json.dumps(snapshot.manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print("[SNAPSHOT] sortie :", snapshot.data.shape)
    print("[SNAPSHOT] semaines 2024 :", params["weeks_2024"])
    print("[SNAPSHOT] dataset :", OUTPUT_FILE)


if __name__ == "__main__":
    main()
