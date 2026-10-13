# Présentation Streamlit

Depuis la racine :

```bash
make install
make presentation
```

Adresse http://127.0.0.1:8501 ; arrêt Ctrl+C. L’entrée app-pres.py charge app/pres-sl/app.py dans le même serveur ; elle peut aussi être passée directement à `uv run --frozen streamlit run app-pres.py`.

Les huit pages, templates, CSS, dix images et quatre polices sont entièrement locaux. La navigation utilise #01 à #08 ; la page de démonstration bascule entre deux captures illustratives. Les libellés d’API dans les captures peuvent précéder le renommage ; les contrats et commandes du README principal font référence.

```bash
uv run --frozen python -m pytest app/pres-sl/tests -p no:cacheprovider
```

Le test du lanceur vérifie la fin du run Streamlit et l’iframe contenant les huit pages et ressources embarquées. Le composant HTML actuel est déprécié par Streamlit mais fonctionne sur la version verrouillée ; sa migration UI n’appartient pas au nettoyage du backend.
