# Plan d'implémentation

## Objectif

Refactoriser progressivement la présentation Streamlit dans `app/presentation` : établir d'abord un squelette de huit diapositives vides et un menu latéral reconstruit avec `st-tailwind`, puis restaurer le contenu de chaque diapositive dans une étape dédiée, sans modifier son ordre ni son sens.

## Contexte

La présentation actuelle repose sur `app_soutenance.py` et `app/soutenance`, où `pages/deck.py` centralise les huit rendus dans 614 lignes. La nouvelle application est créée dans `app/presentation`, avec son propre point d'entrée `app_presentation.py`. Le projet inclut déjà `st-tailwind>=1.3.0`, mais l'application actuelle ne l'initialise ni ne l'emploie encore. `app/soutenance` reste intacte et sert de référence de contenu pendant la migration ; la nouvelle application peut donc être construite et validée sans interrompre la soutenance existante.

## Périmètre

### Inclus

- Un fichier de rendu dédié à chacune des huit diapositives.
- Un routeur léger conservant l'état de session et la structure fonctionnelle du menu latéral.
- La reconstruction du menu avec `st-tailwind`, en reprenant ses informations et son comportement actuels.
- Un premier jalon avec huit diapositives vides, puis un jalon distinct par restauration de slide.
- La préservation exhaustive des textes, visuels, onglets, boutons, interactions et notes orales existants, au terme des huit jalons de contenu.
- L'adaptation des tests et une vérification visuelle progressive.

### Hors périmètre

- Refonte éditoriale ou changement de l'ordre des diapositives.
- Passage à la navigation multipage native de Streamlit.
- Modification des assets, des APIs MLOps ou du comportement des autres applications du dépôt.
- Suppression non nécessaire du CSS dédié aux structures HTML/SVG que `st-tailwind` ne prend pas en charge directement.

## Étape 1 — Créer le squelette de pages et le menu Tailwind

### Objectif

Créer une topologie explicite d'une page Python par diapositive, toutes vides au départ, avec une navigation Tailwind fonctionnelle fondée sur le menu actuel.

### Modifications prévues

- Créer `app/presentation/pages/architecture.py`, `authentication.py`, `training_mlflow_predict.py`, `airflow.py`, `dvc.py`, `monitoring.py`, `ui_demo.py` et `conclusion.py`, chacun exposant une fonction de rendu vide recevant `Slide`.
- Créer ou réduire `deck.py` à un routeur `RENDERERS` important ces huit pages et conservant `render_slide(slide)` comme interface appelée par `app_presentation.py`.
- Initialiser `st_tailwind.initialize_tailwind()` après la configuration de page.
- Reconstruire le menu dans `navigation.py` avec les wrappers `st-tailwind`, en reprenant le logo, le titre, le compteur, les huit libellés, l'état actif, l'ouverture initiale et les boutons Précédent/Suivant du menu actuel.
- Conserver les métadonnées des slides et le contrat de navigation dans `app/presentation` ; `app/soutenance` reste la source de contenu de référence jusqu'aux étapes de restauration.

### Fichiers potentiellement concernés

- `app/presentation/pages/deck.py`
- `app/presentation/pages/architecture.py`
- `app/presentation/pages/authentication.py`
- `app/presentation/pages/training_mlflow_predict.py`
- `app/presentation/pages/airflow.py`
- `app/presentation/pages/dvc.py`
- `app/presentation/pages/monitoring.py`
- `app/presentation/pages/ui_demo.py`
- `app/presentation/pages/conclusion.py`
- `app/presentation/pages/__init__.py`
- `app/presentation/components/navigation.py`
- `app_presentation.py`
- `app/presentation/styles/global.css`

### Validation prévue

- Exécuter une suite de tests adaptée au squelette : les huit entrées de menu, la sélection active et Précédent/Suivant doivent fonctionner ; les assertions de contenu seront temporairement remplacées ou déplacées vers les étapes dédiées.
- Vérifier dans le navigateur que chaque entrée ouvre sa page vide, sans exception, et que le menu conserve son ordre et son comportement.
- Contrôler l'initialisation effective de `st-tailwind` et le rendu du menu sans dépendre d'une navigation multipage native.
- Exécuter `git diff --check`.

### Message de commit proposé

`refactor(presentation): scaffold slide pages and tailwind navigation`

## Étape 2 — Restaurer la page Architecture et lancement

### Objectif

Déplacer et rendre la première slide dans son module dédié, avec son contenu et ses interactions d'origine.

### Modifications prévues

- Déplacer le renderer Architecture, son en-tête, ses cartes et ses notes orales dans `architecture.py`.
- Ne pas reprendre le bouton ni le diagramme Mermaid, retirés à la demande de l'utilisateur.
- Conserver les assets et composants réutilisables existants.
- Employer les primitives `st-tailwind` pour les widgets et layouts Streamlit de la slide, en conservant le CSS dédié aux cartes HTML et au diagramme si nécessaire.

### Fichiers potentiellement concernés

- `app/presentation/pages/architecture.py`
- `app/presentation/pages/deck.py`
- `app/presentation/components/slides.py`
- `app/presentation/tests/test_app.py`

### Validation prévue

- Vérifier le rendu grand écran de la première slide et la présence de tous ses contenus hors diagramme Mermaid.
- Vérifier que les sept autres slides restent accessibles depuis le menu, même vides à ce stade.
- Exécuter les tests ciblés correspondant à la navigation et à la slide Architecture.
- Exécuter `git diff --check`.

### Message de commit proposé

`refactor(presentation): restore architecture slide`

## Étape 3 — Restaurer la page Authentification et JWT

### Objectif

Déplacer et rendre la deuxième slide, y compris l'affichage conditionnel de sa transcription expurgée.

### Modifications prévues

- Déplacer le flux JWT, les cartes de rôles, le bouton de transcription et les notes orales dans `authentication.py`.
- Préserver la clé `show_auth_demo` et les garanties de masquage des secrets.
- Ajouter ou rétablir les assertions de rendu et d'interaction propres à cette slide.

### Fichiers potentiellement concernés

- `app/presentation/pages/authentication.py`
- `app/presentation/pages/deck.py`
- `app/presentation/tests/test_app.py`

### Validation prévue

- Vérifier la slide Authentification, son bouton de transcription et l'absence de secret exposé.
- Exécuter les tests ciblés de navigation et d'authentification, puis `git diff --check`.

### Message de commit proposé

`refactor(presentation): restore authentication slide`

## Étape 4 — Restaurer la page Train, MLflow et Predict

### Objectif

Déplacer la troisième slide et ses quatre onglets MLflow dans `training_mlflow_predict.py`.

### Validation prévue

- Vérifier les onglets Runs, Run W12, Évaluation et Registry, les captures et les contenus associés.
- Exécuter les tests ciblés et `git diff --check`.

### Message de commit proposé

`refactor(presentation): restore training mlflow predict slide`

## Étape 5 — Restaurer la page Data Pull et Airflow

### Objectif

Déplacer la quatrième slide, ses onglets d'exécution et de graphe du DAG dans `airflow.py`.

### Validation prévue

- Vérifier les deux onglets, les visuels, le contenu et les notes orales.
- Exécuter les tests ciblés et `git diff --check`.

### Message de commit proposé

`refactor(presentation): restore airflow slide`

## Étape 6 — Restaurer la page DVC et DagsHub

### Objectif

Déplacer la cinquième slide et sa visionneuse interactive dans `dvc.py`.

### Validation prévue

- Vérifier les contenus, le visuel et les contrôles de zoom/déplacement.
- Exécuter les tests ciblés et `git diff --check`.

### Message de commit proposé

`refactor(presentation): restore dvc slide`

## Étape 7 — Restaurer la page Monitoring et observabilité

### Objectif

Déplacer la sixième slide, ses métriques, alertes et capture Grafana dans `monitoring.py`.

### Validation prévue

- Vérifier les cinq dashboards, les sept alertes, les visuels et le contenu intégral.
- Exécuter les tests ciblés et `git diff --check`.

### Message de commit proposé

`refactor(presentation): restore monitoring slide`

## Étape 8 — Restaurer la page Démonstration UI

### Objectif

Déplacer la septième slide, ses deux onglets et les scénarios nominal/fallback dans `ui_demo.py`.

### Validation prévue

- Vérifier les deux onglets, les captures, les libellés de moteur et le contenu intégral.
- Exécuter les tests ciblés et `git diff --check`.

### Message de commit proposé

`refactor(presentation): restore ui demo slide`

## Étape 9 — Restaurer la page Conclusion et finaliser les garanties

### Objectif

Déplacer la huitième slide dans `conclusion.py`, retirer l'ancien contenu désormais migré de `deck.py` et rétablir l'intégralité de la suite de non-régression.

### Modifications prévues

- Déplacer la grille de conclusion, la chaîne finale, le message à retenir et les notes orales.
- Vérifier que `deck.py` est uniquement le routeur des modules de pages.
- Réactiver ou compléter les assertions de contenu couvrant les huit slides et ajouter une assertion ciblée sur l'initialisation de `st-tailwind`.
- Mettre à jour le changelog français avec les validations réellement exécutées à chaque étape.

### Fichiers potentiellement concernés

- `app/presentation/pages/conclusion.py`
- `app/presentation/pages/deck.py`
- `app/presentation/tests/test_app.py`
- `docs/changes/2026-09-17_design-refactor_pres/changes.md`

### Validation prévue

- Exécuter `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest app/presentation/tests/test_app.py -q -p no:cacheprovider`.
- Vérifier en navigateur les huit diapositives, le menu ouvert/repliable, la sélection active, Précédent/Suivant, les onglets, le diagramme, la transcription Auth et la visionneuse DVC.
- Vérifier à plusieurs largeurs usuelles l'absence de troncature ou de contenu invisible.
- Exécuter `git diff --check` et `git status --short`.

### Message de commit proposé

`test(presentation): protect modular navigation and content`

## Critères de fin

- Le premier jalon fournit huit pages vides sélectionnables et un menu Tailwind complet, sans changer l'ordre ni le comportement de navigation.
- Chaque étape 2 à 9 restaure exactement une slide dans son module dédié ; `deck.py` ne contient plus le contenu des diapositives à la fin du plan.
- Le menu latéral conserve ses huit entrées, son état actif, son ouverture au chargement et les contrôles Précédent/Suivant.
- Tous les contenus présents avant le refactor sont de nouveau accessibles et visibles à la fin de l'étape 9, y compris les captures, onglets, boutons conditionnels et notes orales non projetées.
- `st-tailwind` est initialisé et utilisé pour le menu et les widgets des slides, sans dégrader l'interface.
- Les tests pertinents et les vérifications visuelles définies ci-dessus réussissent ; le changelog documente les modifications effectives.
