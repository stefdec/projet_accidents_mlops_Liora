"""Lance la présentation Streamlit autonome située dans ``app/pres-sl``."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import subprocess
import sys

from streamlit.runtime.scriptrunner import get_script_run_ctx


APP_DIR = Path(__file__).resolve().parent / "app" / "pres-sl"


def main() -> int:
    """Rend la présentation dans Streamlit ou démarre son unique serveur."""
    if get_script_run_ctx(suppress_warning=True) is not None:
        sys.path.insert(0, str(APP_DIR))
        spec = spec_from_file_location("pres_sl_app", APP_DIR / "app.py")
        if spec is None or spec.loader is None:
            raise RuntimeError("Impossible de charger la présentation Streamlit")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        module.main()
        return 0

    command = [
        sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve()),
        *sys.argv[1:],
    ]
    return subprocess.call(command, cwd=APP_DIR)


if __name__ == "__main__":
    if get_script_run_ctx(suppress_warning=True) is not None:
        main()
    else:
        raise SystemExit(main())
