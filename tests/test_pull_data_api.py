import pandas as pd
import pytest
import jwt
from fastapi.testclient import TestClient

from src.pull_data_api.main import app, extract_week, week_bounds_2024


def test_week_bounds_match_ml_snapshot_protocol() -> None:
    assert week_bounds_2024(1) == (
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-08"),
    )
    assert week_bounds_2024(5) == (
        pd.Timestamp("2024-01-29"),
        pd.Timestamp("2024-02-05"),
    )


def test_extract_week_handles_a_month_boundary() -> None:
    source = pd.DataFrame(
        {
            "Num_Acc": [1, 2, 3, 4],
            "accident_date": [
                "2024-01-28",
                "2024-01-29",
                "2024-02-04",
                "2024-02-05",
            ],
            "grav_binaire": [0, 1, 0, 1],
        }
    )

    result = extract_week(source, 5)

    assert result["Num_Acc"].tolist() == [2, 3]


@pytest.mark.parametrize("week", [0, 53])
def test_week_bounds_reject_invalid_week(week: int) -> None:
    with pytest.raises(ValueError):
        week_bounds_2024(week)


def test_pull_endpoint_writes_the_contractual_parquet(tmp_path, monkeypatch) -> None:
    secret = "test-pull-secret-with-at-least-32-bytes"
    monkeypatch.setenv("JWT_SECRET_PULL", secret)
    monkeypatch.setenv("SHARED_DATA_DIRECTORY", str(tmp_path))
    app.state.dataset = pd.DataFrame(
        {
            "Num_Acc": [1, 2],
            "accident_date": ["2024-01-01", "2024-01-08"],
            "grav_binaire": [0, 1],
        }
    )
    token = jwt.encode({"username": "test"}, secret, algorithm="HS256")
    client = TestClient(app)

    response = client.get(
        "/pull_data?week=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["record_count"] == 1
    assert (tmp_path / "accidents_2024_w01.parquet").exists()
