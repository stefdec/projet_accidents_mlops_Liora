import requests

from scripts.predict_api_smoke_test import post_with_startup_retry


class _Response:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_startup_retry_recovers_after_connection_reset(monkeypatch) -> None:
    responses = iter(
        [
            requests.ConnectionError("service en démarrage"),
            _Response(503),
            _Response(200),
        ]
    )

    def fake_post(*args, **kwargs):
        result = next(responses)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    response = post_with_startup_retry(
        "http://predict-api/predict",
        startup_timeout=1,
        request_timeout=1,
    )

    assert response.status_code == 200
