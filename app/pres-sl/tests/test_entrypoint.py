from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_entrypoint_completes_and_renders_all_slides():
    entrypoint = Path(__file__).resolve().parents[3] / 'app-pres.py'
    app = AppTest.from_file(str(entrypoint), default_timeout=20).run()
    assert not app.exception
    frames = app.get('iframe')
    assert len(frames) == 1
    document = frames[0].proto.srcdoc
    assert all(f'"{number:02d}":' in document for number in range(1, 9))
    assert 'assets/images/' not in document
    assert 'assets/fonts/' not in document
