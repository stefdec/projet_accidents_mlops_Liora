## Créer le squelette de présentation et le menu Tailwind

**Message de commit**

`refactor(presentation): scaffold slide pages and tailwind navigation`

**Ce qui a changé**

- Création de l'application isolée `app/presentation` et de son point d'entrée `app_presentation.py`.
- Création de huit modules de slides volontairement vides, d'un routeur et d'un état de navigation dédiés.
- Création d'un menu latéral reprenant les huit sections, le compteur, la sélection active et les contrôles précédent/suivant de la soutenance existante.
- Initialisation de `st-tailwind` et usage de ses wrappers pour les boutons et la grille de contrôles du menu.
- Alignement du contenu du menu à 10 px du haut, masquage du bouton de repli et ajout d'un rail vertical reliant les pastilles numérotées.
- Suppression de l'espace réservé par les cadres techniques de `st-tailwind`, remontée effective du bloc marque en haut du menu et prolongement continu du rail entre les pastilles.

**Pourquoi**

- Poser une nouvelle base modulaire dans `app/presentation` sans modifier `app/soutenance`, qui demeure la référence de contenu pour les étapes suivantes.
- Permettre de restaurer et de valider chaque slide indépendamment tout en conservant une navigation stable.

**Fichiers**

- `app_presentation.py`
- `app/presentation/config.py`
- `app/presentation/components/navigation.py`
- `app/presentation/pages/*.py`
- `app/presentation/styles/global.css`
- `app/presentation/tests/test_app.py`

**Validation**

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest app/presentation/tests/test_app.py -q -p no:cacheprovider` : 6 tests réussis.
- `impeccable detect --json --scope layout app/presentation app_presentation.py` : aucune anomalie détectée.
- `git diff --check` : réussi.

- Vérification visuelle effectuée dans le navigateur aux formats bureau et mobile après correction.

## Coloriser et affirmer la slide Architecture

**Message de commit**

`refactor(presentation): redesign architecture slide`

**Ce qui a changé**

- Installation d'une palette structurée autour de l'encre marine et d'un accent spectral, avec des cartes volontairement neutres en blanc cassé et gris froid.
- Transformation de l'en-tête en bandeau sombre avec une ligne spectrale et consolidation des responsabilités transverses dans un rail continu.
- Suppression de tous les rayons d'angle sur la slide, les contrôles du menu et le logo, tout en conservant les pastilles circulaires de progression.
- Renforcement des connecteurs, de la hiérarchie typographique et du comportement des libellés longs à 1440 px.
- Réduction de la saturation des cartes après revue visuelle, la couleur restant limitée à leurs filets de catégorisation.
- Réduction du contraste vers une palette grise apaisée, avec un en-tête légèrement plus sombre et une barre claire monochrome.
- Application d'un rayon moyen partagé aux surfaces et contrôles de la présentation.
- Uniformisation de la grille des cartes : trois colonnes identiques, hauteurs communes et gouttières constantes.
- Remplacement des colonnes réservées aux connecteurs par des flèches positionnées dans les espaces entre cartes.
- Réalignement de l'en-tête contre le bord supérieur et suppression de son rayon afin d'en faire une bande pleine.
- Ajout d'une hiérarchie de flux plus expressive : surfaces légèrement teintées, séparateurs internes et connecteurs fins entre les étapes.
- Correction explicite du rayon des cartes de la première ligne, cohérent avec les autres cartes de la présentation.
- Renforcement de la couleur des surfaces fonctionnelles et suppression des bordures génériques des cartes.
- Recomposition des trois cartes transverses comme des panneaux de système : nom de technologie dominant, rôle et effet séparés par un filet contextuel.
- Remplacement des aplats et contours de cartes par des surfaces transparentes et des filets colorés fins pour une lecture plus discrète.
- Refonte complète de la première slide : en-tête blanc, colonne de services bleu nuit, canevas vertical inspiré de Miro et bande de repères de lancement.
- Réorganisation des repères inférieurs en une ligne « Démarrage / Sécurité / Observabilité » pour distinguer nettement la plateforme, le flux et les garanties opérationnelles.

**Pourquoi**

- Éloigner la présentation d'une composition générique de cartes blanches et lui donner une identité plus reconnaissable sur grand écran.
- Respecter la demande d'une géométrie entièrement angulaire sans perdre la lisibilité du parcours.

**Fichiers**

- `app/presentation/styles/global.css`
- `app/presentation/styles/architecture.css`
- `docs/changes/2026-09-17_design-refactor_pres/changes.md`

**Validation**

- Vérification visuelle en 1440 × 1000 avec le menu ouvert : réussie, sans troncature ni débordement.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest app/presentation/tests/test_app.py -q -p no:cacheprovider` : 6 tests réussis.
- `impeccable detect --json --scope layout app/presentation/styles/global.css app/presentation/styles/architecture.css` : aucune anomalie détectée.
- `git diff --check` : réussi.

## Formaliser le contexte produit de la présentation

**Message de commit**

`docs(presentation): capture product context`

**Ce qui a changé**

- Création du contexte produit Impeccable, limité à `app/presentation`, avec le public, le double objectif de démonstration et de support oral, les huit parties et les preuves disponibles.
- Enregistrement des références visuelles confirmées « Iridescent Cloud Edge » et « Fluid Ink Basin » sans anticiper leur interprétation graphique.
- Configuration du workflow Impeccable en mode code-first.

**Pourquoi**

- Donner aux prochains travaux de conception une source durable de vérité produit sans confondre les décisions produit et la future direction visuelle.

**Fichiers**

- `PRODUCT.md`
- `.impeccable/config.json`
- `docs/changes/2026-09-17_design-refactor_pres/changes.md`

**Validation**

- Vérification du schéma produit Impeccable et du JSON de configuration.
- `git diff --check`.

## Restaurer la slide Architecture et lancement

**Message de commit**

`refactor(presentation): restore architecture slide`

**Ce qui a changé**

- Restauration du titre, de la promesse, du flux fonctionnel, des responsabilités transverses, des faits de lancement et des notes orales de la première slide.
- Utilisation de `st-tailwind` pour la grille Streamlit et création de primitives partagées pour les en-têtes et les notes des futures slides.
- Séparation des styles propres à la slide dans `styles/architecture.css`, chargé après les fondations globales.
- Retrait du bouton et du diagramme Mermaid conformément à la décision utilisateur.
- Enregistrement de la projection grand écran comme seul contexte de rendu à prendre en charge.

**Pourquoi**

- Migrer fidèlement la première partie depuis `app/soutenance` tout en posant une structure CSS modulaire pour les sept prochaines slides.
- Concentrer la projection sur les informations essentielles sans interaction Mermaid secondaire.

**Fichiers**

- `app/presentation/components/slides.py`
- `app/presentation/pages/architecture.py`
- `app/presentation/styles/architecture.css`
- `app/presentation/styles/global.css`
- `app/presentation/styles/theme.py`
- `app/presentation/tests/test_app.py`
- `PRODUCT.md`
- `docs/changes/2026-09-17_design-refactor_pres/plan.md`

**Validation**

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest app/presentation/tests/test_app.py -q -p no:cacheprovider` : 6 tests réussis.
- Vérification visuelle de la slide complète en 1440 × 1000 : réussie, sans défilement ni troncature.
- `impeccable detect --json --scope layout ...` : aucune anomalie détectée.
- `git diff --check` : réussi.
