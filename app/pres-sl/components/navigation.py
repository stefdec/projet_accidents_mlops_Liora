"""Navigation visuelle et comportementale fidèle au rail de v3."""

from __future__ import annotations

import json

from pages import architecture_lancement, authentification_jwt, conclusion, data_pull_airflow, demonstration_ui, dvc_dagshub, monitoring_observabilite, train_mlflow_predict
from pages.registry import SLIDES
from components.renderer import stylesheet


def document() -> str:
    renderers = [architecture_lancement.render, authentification_jwt.render, train_mlflow_predict.render, data_pull_airflow.render, dvc_dagshub.render, monitoring_observabilite.render, demonstration_ui.render, conclusion.render]
    fragments = {number: renderer() for (number, _, _), renderer in zip(SLIDES, renderers, strict=True)}
    links = "".join(f'<a class="slide-link" data-slide="{number}" data-slide-number="{number}" href="#{number}">{title}</a>' for number, title, _ in SLIDES)
    return f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>{stylesheet()}</style></head>
<body class="reference-page"><div class="presentation-shell"><aside class="reference-sidebar" aria-label="Navigation de la présentation">
<a class="reference-brand" href="#01"><span class="reference-logo"><span></span><i></i></span><span><p>Accidents <strong>MLOps</strong></p><small>Présentation du projet</small></span></a>
<div class="reference-outline-heading"><span>Plan de la soutenance</span><strong><span id="progress">01</span><small> / 08</small></strong></div>
<nav class="reference-slide-nav" aria-label="Slides">{links}</nav><div class="reference-controls"><p>Navigation</p><div><a id="previous" href="#"><span class="nav-icon">‹</span><span>Précédent</span></a><a id="next" href="#"><span>Suivant</span><span class="nav-icon">›</span></a></div></div></aside>
<section class="presentation-page" id="slide-root"></section></div>
<script>const slides={json.dumps(fragments, ensure_ascii=False)};let current='01';const root=document.querySelector('#slide-root');function go(id){{if(!slides[id])return;current=id;root.innerHTML=slides[id];document.querySelectorAll('.slide-link').forEach(a=>{{let on=a.dataset.slide===id;a.classList.toggle('active',on);a.toggleAttribute('aria-current',on)}});progress.textContent=id;previous.setAttribute('aria-disabled',id==='01');next.setAttribute('aria-disabled',id==='08');history.replaceState(null,'','#'+id)}}document.querySelectorAll('.slide-link').forEach(a=>a.onclick=e=>{{e.preventDefault();go(a.dataset.slide)}});previous.onclick=e=>{{e.preventDefault();go(String(Math.max(1,+current-1)).padStart(2,'0'))}};next.onclick=e=>{{e.preventDefault();go(String(Math.min(8,+current+1)).padStart(2,'0'))}};document.addEventListener('click',e=>{{let b=e.target.closest('.ui-tabs button');if(!b)return;document.querySelectorAll('.ui-tabs button').forEach(x=>{{let on=x===b;x.classList.toggle('active',on);x.setAttribute('aria-selected',on)}});let image=document.querySelector('#ui-screen');if(image){{image.src=b.dataset.image;image.alt=b.dataset.alt}}}});go(location.hash.slice(1)||'01');</script></body></html>'''
