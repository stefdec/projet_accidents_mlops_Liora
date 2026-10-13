FROM python:3.12-slim

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --only-group exporters --no-install-project

COPY monitoring/exporters/ ./monitoring/exporters/
CMD ["uvicorn", "monitoring.exporters.drift.drift_metrics:app", "--host", "0.0.0.0", "--port", "8001"]
