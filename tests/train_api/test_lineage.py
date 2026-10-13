from __future__ import annotations

from pathlib import Path

from src.train_api.config import Settings
from src.train_api.lineage import (
    build_dataset_digest,
    digest_manifest,
    digest_ml_config,
    sha256_file,
    source_lineage,
)


def test_file_digest_is_stable_and_changes_when_file_content_changes(tmp_path: Path) -> None:
    source = tmp_path / "input.parquet"
    source.write_bytes(b"first-content")

    first = sha256_file(source, chunk_size=2)
    second = sha256_file(source, chunk_size=3)
    source.write_bytes(b"changed-content")

    assert first == second
    assert first.startswith("sha256:")
    assert sha256_file(source) != first


def test_manifest_and_ml_config_digests_are_deterministic_and_sensitive() -> None:
    manifest = {"rows": 3, "weekly_files": ["w01.parquet"]}
    same_manifest_different_order = {"weekly_files": ["w01.parquet"], "rows": 3}
    config = {"threshold": 0.48, "model": {"seed": 42}}

    assert digest_manifest(manifest) == digest_manifest(same_manifest_different_order)
    assert digest_ml_config(config) != digest_ml_config({"threshold": 0.49, "model": {"seed": 42}})


def test_dataset_digest_aggregates_inputs_manifest_and_ml_config() -> None:
    kwargs = {
        "manifest": {"rows": 3},
        "ml_config": {"threshold": 0.48},
    }

    first = build_dataset_digest(["sha256:b", "sha256:a"], **kwargs)
    same_inputs_other_order = build_dataset_digest(["sha256:a", "sha256:b"], **kwargs)
    changed_config = build_dataset_digest(
        ["sha256:a", "sha256:b"],
        manifest={"rows": 3},
        ml_config={"threshold": 0.49},
    )

    assert first == same_inputs_other_order
    assert first.startswith("sha256:")
    assert changed_config != first


def test_source_lineage_uses_the_injected_setting_without_invoking_git() -> None:
    settings = Settings(source_git_commit="build-injected-commit")

    assert source_lineage(settings) == {"source_git_commit": "build-injected-commit"}
