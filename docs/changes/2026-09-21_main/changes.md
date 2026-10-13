## Éviter le second serveur de la présentation

**Message de commit**

`fix(presentation): render root launcher in the active streamlit server`

**Ce qui a changé**

- `app-pres.py` rend `app/pres-sl/app.py` dans la session Streamlit existante lorsqu'il est lancé avec `streamlit run`.
- Le lancement avec `python app-pres.py` démarre un unique serveur sur ce même point d'entrée, en transmettant les arguments CLI.
- La commande de lancement est clarifiée dans le README de la présentation.

**Pourquoi**

- Le lanceur précédent créait un second processus Streamlit lorsqu'il était lui-même exécuté avec `streamlit run`, provoquant l'ouverture d'un second port.

**Fichiers**

- `app-pres.py`
- `app/pres-sl/README.md`
- `docs/changes/2026-09-21_main/changes.md`

**Validation**

- À compléter après vérification des deux modes de lancement.
