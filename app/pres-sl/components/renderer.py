"""Rendu HTML isolé pour conserver la géométrie exacte de la référence."""

from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path

import streamlit.components.v1 as components


ROOT = Path(__file__).parents[1]


def data_uri(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime or 'application/octet-stream'};base64,{encoded}"


def localise_assets(markup: str) -> str:
    """Remplace tous les chemins relatifs par des ressources embarquées locales."""
    def replace(match: re.Match[str]) -> str:
        kind, filename = match.group(1), match.group(2)
        return data_uri(ROOT / "assets" / kind / filename)

    return re.sub(r"(?:\.\./)?assets/(images|fonts)/([\w.-]+)", replace, markup)


def slide_fragment(template_name: str) -> str:
    source = (ROOT / "templates" / template_name).read_text(encoding="utf-8")
    main = re.search(r"(<main class=\"slide-main\">.*?</main>)", source, re.S)
    if main is None:
        raise ValueError(f"Gabarit invalide : {template_name}")
    return localise_assets(main.group(1))


def stylesheet() -> str:
    return localise_assets((ROOT / "styles" / "global.css").read_text(encoding="utf-8"))


def render(document: str) -> None:
    components.html(document, height=1080, scrolling=True)
