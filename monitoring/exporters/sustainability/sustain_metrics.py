from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest


app = FastAPI(
    title="Sustainability Metrics Exporter"
)

EMISSIONS_FILE = Path(
    "reports/carbon/emissions.csv"
)


TRAINING_CO2 = Gauge(
    "training_co2_kg",
    "CO2 emissions of the latest training run in kg",
)

TRAINING_ENERGY = Gauge(
    "training_energy_kwh",
    "Energy consumed by the latest training run in kWh",
)

TRAINING_DURATION = Gauge(
    "training_duration_seconds",
    "Duration of the latest training run in seconds",
)

TRAINING_CPU_ENERGY = Gauge(
    "training_cpu_energy_kwh",
    "CPU energy consumed by the latest training run in kWh",
)

TRAINING_GPU_ENERGY = Gauge(
    "training_gpu_energy_kwh",
    "GPU energy consumed by the latest training run in kWh",
)

TRAINING_RAM_ENERGY = Gauge(
    "training_ram_energy_kwh",
    "RAM energy consumed by the latest training run in kWh",
)
TRAINING_LAST_RUN = Gauge(
    "training_last_run_timestamp_seconds",
    "Epoch du dernier run d'entraînement (colonne timestamp de emissions.csv)",
)
TRAINING_LAST_RUN.set(0)

def update_metrics() -> None:

    if not EMISSIONS_FILE.exists():
        return

    df = pd.read_csv(EMISSIONS_FILE)

    if df.empty:
        return

    latest = df.iloc[-1]
    
    ts = latest.get("timestamp")
    if ts is not None and str(ts).strip():
        try:
            TRAINING_LAST_RUN.set(pd.Timestamp(ts).timestamp())
        except (ValueError, TypeError):
            pass

    TRAINING_CO2.set(
        float(latest.get("emissions", 0) or 0)
    )

    TRAINING_ENERGY.set(
        float(latest.get("energy_consumed", 0) or 0)
    )

    TRAINING_DURATION.set(
        float(latest.get("duration", 0) or 0)
    )

    TRAINING_CPU_ENERGY.set(
        float(latest.get("cpu_energy", 0) or 0)
    )

    TRAINING_GPU_ENERGY.set(
        float(latest.get("gpu_energy", 0) or 0)
    )

    TRAINING_RAM_ENERGY.set(
        float(latest.get("ram_energy", 0) or 0)
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "emissions_file_exists": EMISSIONS_FILE.exists(),
    }


@app.get("/metrics")
def metrics():

    update_metrics()

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )