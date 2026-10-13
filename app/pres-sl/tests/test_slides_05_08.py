import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from pages import conclusion, demonstration_ui, dvc_dagshub, monitoring_observabilite

def test_last_four_reference_content() -> None:
    checks = [(dvc_dagshub.render(), "DVC garantit"), (monitoring_observabilite.render(), "7 alertes"), (demonstration_ui.render(), "POST /api/predict"), (conclusion.render(), "Notre engagement")]
    for page, text in checks:
        assert text in " ".join(page.split()) and "data:image/" in page
    assert "ui2.jpg" not in demonstration_ui.render()
