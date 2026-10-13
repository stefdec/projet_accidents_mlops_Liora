## Navigation à deux onglets et bloc de prédiction figé

**Message de commit**

`feat(interface): add tabbed navigation and lock prediction action banner`

**Ce qui a changé**

- Ajout de la navigation à deux onglets dans `App.jsx` ("Principal" et "Détails").
- Répartition des zones : Onglet 1 avec Caractéristiques (35%) et Lieux & Environnement (65%), Onglet 2 avec Véhicules & Chocs 3D (50%) et Usagers & Victimes (50%).
- Positionnement figé et permanent du bloc d'action "Envoyer" et de la carte du résultat de prédiction sur tous les onglets.
- Suppression du bloc de métadonnées secondaires ("Probabilité d'hospitalisation / décès", jauge, modèle actif, statut décision, temps d'inférence) dans `PredictionResult.jsx`.

**Pourquoi**

- Améliorer l'ergonomie et la lisibilité globale de l'interface en offrant un espace agrandi pour la carte et les modélisateurs 3D.
- Garantir que l'opérateur puisse soumettre la prédiction à tout moment quel que soit l'onglet affiché.

**Fichiers**

- `interface/src/App.jsx`
- `interface/src/components/PredictionResult.jsx`

**Validation**

- Exécution de `npm run build` : compilé avec succès.

## Automatisation de la période et gestion de l'éclairage public

**Message de commit**

`feat(interface): automate period and luminosity calculation from incident timestamp`

**Ce qui a changé**

- Suppression du choix manuel de la période dans `CaracteristiquesZone.jsx` (définie automatiquement d'après l'horodatage : nuit 00h-06h, matin 06h-12h, après-midi 12h-18h, soir 18h-00h).
- Automatisation du mode de luminosité ambiante (Plein jour de 06h à 18h, Crépuscule de 18h à 22h, Nuit de 22h à 06h).
- Définition des options d'éclairage public dans `constants.js` (3: Nuit sans éclairage public, 4: Nuit avec éclairage public non allumé, 5: Nuit avec éclairage public allumé).

**Pourquoi**

- Automatiser la saisie des informations temporelles et lumineuses dérivables de l'horodatage pour accélérer la prise d'appel d'urgence.

**Fichiers**

- `interface/src/config/constants.js`
- `interface/src/components/zones/CaracteristiquesZone.jsx`

**Validation**

- Exécution de `npm run build` : compilé avec succès.

## Agrandissement de la zone Lieux, bornes PR Overpass et fallbacks

**Message de commit**

`feat(interface): enlarge location map, add Overpass PR lookup and empty field fallbacks`

**Ce qui a changé**

- Redimensionnement de la carte OpenStreetMap Leaflet (passée de 200px à 340px).
- Ajout de l'interrogation dynamique via l'API Overpass (`highway=milestone`, `highway=motorway_junction`) et affichage automatique au bas de la carte de la phrase de situation ("Sinistre situé entre borne PR X et borne PR Y...").
- Intégration d'un calque GeoJSON (`L.geoJSON()`) lié nativement à la carte Leaflet.
- Ajout d'options vides par défaut (`""`) pour les sélecteurs de `LieuxZone.jsx` (catr, atm, surf, circ, infra, situ).
- Application des fallbacks par défaut lors de la soumission de la prédiction dans `App.jsx`.

**Pourquoi**

- Permettre à l'opérateur d'identifier immédiatement si une information n'a pas été saisie ou fournie par une API, tout en garantissant des valeurs par défaut valides lors de la prédiction.
- Localiser précisément le sinistre par rapport aux repères routiers officiels et sorties d'autoroute.

**Fichiers**

- `interface/src/components/zones/LieuxZone.jsx`
- `interface/src/components/OpenStreetMapViewer.jsx`
- `interface/src/App.jsx`

**Validation**

- Exécution de `npm run build` : compilé avec succès.

## Options 3+ véhicules et duplication pour le véhicule B

**Message de commit**

`feat(interface): add multi-vehicle collision options and duplicate controls for vehicle B`

**Ce qui a changé**

- Agrandissement des 2 modélisateurs 3D dans l'Onglet 2.
- Ajout du sous-menu "Type de collision" pour le choix "3+ Véhicules" (Carambolage = 4, Accordéon = 5).
- Réglage des valeurs par défaut pour la motorisation (0), la manœuvre (0) et l'obstacle mobile (1 si >=2 véhicules, 4 si 1 seul véhicule).
- Duplication des sélecteurs de motorisation, manœuvre avant choc et obstacle mobile pour le Véhicule B dès que 2+ véhicules sont concernés.

**Pourquoi**

- Faciliter la qualification précise des chocs multiples et carambolages tout en permettant une caractérisation indépendante du second véhicule impliqué.

**Fichiers**

- `interface/src/components/zones/VehiculesZone.jsx`
- `interface/src/config/constants.js`

**Validation**

- Exécution de `npm run build` : compilé avec succès.

## Formulaires dynamiques des victimes jusqu'à 5 usagers et titres épurés

**Message de commit**

`feat(interface): support up to 5 victims with cleaned titles and default driver role`

**Ce qui a changé**

- Génération dynamique de 1 à 5 formulaires de victimes dans `UsagersZone.jsx` selon le nombre estimé de blessés.
- Suppression des mentions `(principale)` et `(secondaire)` dans les titres des victimes (titres épurés: "Victime 1", "Victime 2", etc.).
- Fixation du rôle par défaut à Conducteur (`1`) pour les victimes.

**Pourquoi**

- Permettre de renseigner plusieurs victimes jusqu'à un maximum de 5 usagers lors des accidents graves sans alourdir le titre des formulaires.

**Fichiers**

- `interface/src/components/zones/UsagersZone.jsx`

**Validation**

- Exécution de `npm run build` : compilé avec succès.

## Extension à 6 formulaires de victimes et documentation technique rapport.md

**Message de commit**

`docs(interface): support up to 6 victim forms and add technical documentation rapport.md`

**Ce qui a changé**

- Extension du nombre maximal de formulaires de victimes détaillés à 6 dans `UsagersZone.jsx`.
- Déblocage du compteur du nombre estimé de blessés sans limite d'incrémentation (avec indication si > 6 blessés).
- Création du rapport technique complet [rapport.md](file:///home/hado/Projets/projet_accidents_MLOps/interface/rapport.md) présentant toutes les fonctionnalités de l'interface et son fonctionnement par rapport aux données.

**Pourquoi**

- Répondre au besoin de saisie de jusqu'à 6 victimes lors d'accidents graves tout en conservant un compteur global illimité de blessés.
- Fournir une documentation technique et fonctionnelle de référence pour la présentation de l'interface.

**Fichiers**

- `interface/src/components/zones/UsagersZone.jsx`
- `interface/rapport.md`

**Validation**

- Exécution de `npm run build` : compilé avec succès.
