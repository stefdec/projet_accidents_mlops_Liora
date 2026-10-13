"""Static guardrails for the isolated, direct-Python training API."""

from __future__ import annotations

import ast
from pathlib import Path

from src.train_api.schemas import TrainingResult

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / "train_api"
REQUIREMENTS = PACKAGE_ROOT / "requirements.txt"
FORBIDDEN_IMPORT_PREFIXES = ("subprocess", "dvc", "pipeline", "monitoring")
FORBIDDEN_CALLS = {"os.system", "os.popen", "subprocess.Popen", "subprocess.run"}


def _architecture_violations(root: Path) -> list[str]:
    """Return source-level violations; exposed to make negative tests possible."""
    violations: list[str] = []
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                        violations.append(f"{path.name}: import {name.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if (module.startswith("src.train_api.utils")
                    or module.startswith("projet_accidents_mlops")):
                    violations.append(f"{path.name}: from {module}")
                elif module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    violations.append(f"{path.name}: from {module}")
            elif isinstance(node, ast.Call):
                call_name = _call_name(node.func)
                if call_name in FORBIDDEN_CALLS:
                    violations.append(f"{path.name}: {call_name}")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value.lower()
                if "uv run" in value or value.endswith(".py") and "python " in value:
                    violations.append(f"{path.name}: external command literal")
                if value in {"params.yaml", "dvc.lock"}:
                    violations.append(f"{path.name}: legacy runtime file")
    return violations


def _call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def test_active_package_has_no_external_process_or_legacy_imports() -> None:
    assert _architecture_violations(PACKAGE_ROOT) == []


def test_negative_fixture_detects_external_process(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text("import subprocess\nsubprocess.run(['x'])\n", encoding="utf-8")
    assert _architecture_violations(tmp_path) == [
        "bad.py: import subprocess",
        "bad.py: subprocess.run",
    ]


def test_active_requirements_exclude_dvc_and_the_contract_has_airflow_handoff() -> None:
    requirements = REQUIREMENTS.read_text(encoding="utf-8").lower()
    assert "dvc" not in requirements
    assert {"mlflow_run_id", "model_uri", "registered_model_name", "candidate_version", "champion_version", "dataset_digest"} <= set(TrainingResult.model_fields)
