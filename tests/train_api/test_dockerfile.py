from __future__ import annotations

from pathlib import Path


DOCKERFILE = Path("src/train_api/Dockerfile")


def test_production_image_is_isolated_non_root_and_direct() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in content
    assert "COPY src/train_api/requirements.txt" in content
    assert "uv pip install" in content
    assert "--requirement requirements.txt" in content
    assert "ARG APP_UID=1000" in content
    assert "ARG APP_GID=1000" in content
    assert "COPY --chown=app:app src/train_api/ ./src/train_api/" in content
    assert "USER app" in content
    assert 'CMD ["uvicorn", "src.train_api.main:app"' in content
    assert "WORKDIR /app" in content
    assert "PYTHONDONTWRITEBYTECODE=1" in content
    assert "SOURCE_GIT_COMMIT" in content


def test_dockerfile_excludes_legacy_code_tools_and_runtime_writes() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8").lower()

    assert "copy ." not in content
    assert "training_cli" not in content
    assert "pipeline" not in content
    assert ".git" not in content
    assert "dvc" not in content
    assert "git install" not in content
    assert "uv run" not in content
    assert "base_dataset_path=/var/lib/train-api/input" in content
    assert "artifact_root=/var/lib/train-api/artifacts" in content
    assert "state_db_path=/var/lib/train-api/state" in content


def test_dockerignore_excludes_generated_files() -> None:
    ignored = Path("src/train_api/.dockerignore").read_text(encoding="utf-8")
    assert "__pycache__/" in ignored
    assert "*.sqlite3" in ignored
