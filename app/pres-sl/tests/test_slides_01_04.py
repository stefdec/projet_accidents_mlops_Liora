import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from pages import architecture_lancement, authentification_jwt, data_pull_airflow, train_mlflow_predict


def test_first_four_reference_content() -> None:
    checks = [
        (architecture_lancement.render(), "Airflow", "archi.png"),
        (authentification_jwt.render(), "Bearer token", "auth.png"),
        (train_mlflow_predict.render(), "MLflow", "mlflow.jpeg"),
        (data_pull_airflow.render(), "3 tentatives", "airflow_dag2.png"),
    ]
    for page, text, asset in checks:
        assert text in page
        assert asset not in page  # l'asset est bien embarqué, jamais chargé depuis v3.
        assert "data:image/" in page
