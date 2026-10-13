"""Deterministic input lineage without Git, DVC, or external services."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from src.train_api.config import Settings


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Hash a file incrementally so large inputs are never read all at once."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def digest_manifest(manifest: Mapping[str, object]) -> str:
    """Return a canonical SHA-256 digest for snapshot metadata."""
    return _digest_json(manifest)


def digest_ml_config(config: Mapping[str, object]) -> str:
    """Return a canonical SHA-256 digest for immutable ML parameters."""
    return _digest_json(config)


def build_dataset_digest(
    input_digests: Iterable[str],
    *,
    manifest: Mapping[str, object],
    ml_config: Mapping[str, object],
) -> str:
    """Aggregate input, snapshot, and ML configuration lineage deterministically."""
    return _digest_json(
        {
            "input_digests": sorted(input_digests),
            "manifest_digest": digest_manifest(manifest),
            "ml_config_digest": digest_ml_config(ml_config),
        }
    )


def source_lineage(settings: Settings) -> dict[str, str]:
    """Expose the build-injected source identifier without invoking Git."""
    return {"source_git_commit": settings.source_git_commit}


def _digest_json(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
