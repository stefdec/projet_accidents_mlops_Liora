# Plan d'implémentation — Refonte de l'interface utilisateur

## Objectif

Réorganiser et améliorer l'interface web de régulation d'urgence (dossier `interface`) en 2 onglets distincts ("Principal" et "Détails"), automatiser l'horodatage et la luminosité, gérer les données spatiales (bornes kilométriques PR, sorties d'autoroute et éclairage GeoJSON), dupliquer les caractéristiques pour le véhicule B, étendre la gestion des victimes jusqu'à 5 usagers, et adapter les comportements par défaut des formulaires.

## Contexte

L'interface actuelle concentre 4 zones sur une même vue, ce qui réduit la lisibilité de la carte et des modélisateurs 3D. De plus, certaines métadonnées de prédiction inutiles doivent être retirées, et l'intégration de données spatiales (OpenStreetMap/Overpass et GeoJSON) permettra d'enrichir automatiquement la localisation et l'état d'éclairage public.

## Périmètre

### Inclus

- **Onglets & Navigation** : Séparation en Onglet 1 ("Principal" : Caractéristiques, Lieux & Environnement) et Onglet 2 ("Détails" : Véhicules & Chocs 3D, Usagers & Victimes).
- **Bouton & Résultat Figé** : Le bouton "Envoyer" et le résultat de prédiction restent constamment visibles et accessibles sur les deux onglets.
- **Zone 1 (Caractéristiques)** : Période masquée (calculée automatiquement selon l'heure de 00h à 24h). Luminosité auto-déterminée (Plein jour / Crépuscule / Nuit), choix utilisateur/API restreint aux modalités d'éclairage (3: sans éclairage public, 4: éclairage non allumé, 5: éclairage allumé).
- **Zone 2 (Lieux & Environnement)** : Agrandissement de la carte, des panneaux VMA et des sélecteurs. Gestion des cases vides par défaut avec fallback automatique à la soumission. Requête Overpass API pour bornes kilométriques (PR) et sorties d'autoroute. Détection GeoJSON d'éclairage public.
- **Zone 3 (Véhicules & Chocs 3D)** : Agrandissement des 2 modélisateurs. Sous-menu collision spécifique pour "3+ Véhicules" (Carambolage = 4, Accordéon = 5). Duplication de la motorisation, manœuvre et obstacle mobile pour le Véhicule B. Valeurs par défaut ajustées.
- **Zone 4 (Usagers & Victimes)** : Jusqu'à 5 fiches de victimes dynamiques (selon le nombre estimé de blessés). Suppression des termes "(principale)" et "(secondaire)". Rôle par défaut = Conducteur.
- **Formulaire / Prédiction** : Suppression du pavé de métadonnées "Probabilité d'hospitalisation / décès" (modèle actif, statut décision, temps d'inférence).

### Hors périmètre

- Modifications des API backend Python (`predict_api_v2`, `auth_api`).

---

## Étape 1 — Navigation par Onglets, Zone Figée d'Action & Nettoyage de PredictionResult

### Objectif
Mettre en place la navigation à deux onglets dans `App.jsx`, figer la zone de soumission/résultat de prédiction en bas d'écran, et retirer la section de métadonnées secondaires de `PredictionResult.jsx`.

### Modifications prévues
- Dans `src/App.jsx` : Ajouter l'état d'onglet actif (`activeTab`: 'principal' | 'details').
- Structurer le layout avec des onglets visuels modernes en haut, affichant soit (Zone 1 + Zone 2) soit (Zone 3 + Zone 4).
- Conserver le bloc de prédiction et de dispatch figé en bas sur tous les onglets.
- Dans `src/components/PredictionResult.jsx` : Retirer la section "Probabilité d'hospitalisation / décès" (graphique/jauge, modèle actif, statut décision, temps d'inférence).

### Fichiers potentiellement concernés
- `interface/src/App.jsx`
- `interface/src/components/PredictionResult.jsx`

### Validation prévue
- Lancement de `npm run dev` dans `interface`.
- Navigation fluide entre l'onglet "Principal" et l'onglet "Détails".
- Vérification que le bouton "Envoyer" et la carte de résultat restent visibles sur les deux onglets.

### Message de commit proposé
`feat(interface): add tabbed navigation and lock prediction action banner`

---

## Étape 2 — Automatisation de la Zone Caractéristiques (Horodatage, Luminosité, Éclairage)

### Objectif
Automatiser la période de la journée et la luminosité générale à partir de l'horodatage du sinistre, et proposer les options d'éclairage public.

### Modifications prévues
- Dans `src/config/constants.js` : Mettre à jour `LUM_OPTIONS` avec les libellés exacts (1: Plein jour, 2: Crépuscule ou aube, 3: Nuit sans éclairage public, 4: Nuit avec éclairage public non allumé, 5: Nuit avec éclairage public allumé).
- Dans `src/components/zones/CaracteristiquesZone.jsx` : Retirer la sélection manuelle de la période (calculée en arrière-plan d'après l'heure).
- Définir automatiquement la luminosité de base (`Plein jour` de 06h à 18h, `Crépuscule/Aube` de 18h à 22h, `Nuit` de 22h à 06h).
- Pour la nuit, activer le choix entre les modalités 3, 4 et 5 (interagissant avec les informations d'éclairage).

### Fichiers potentiellement concernés
- `interface/src/config/constants.js`
- `interface/src/components/zones/CaracteristiquesZone.jsx`
- `interface/src/App.jsx`

### Validation prévue
- Tester différentes heures d'ouverture de sinistre et vérifier le calcul automatique de la période et de la luminosité.

### Message de commit proposé
`feat(interface): automate period and luminosity calculation from incident timestamp`

---

## Étape 3 — Zone Lieux & Environnement (Layout, Bornes PR Overpass, GeoJSON & Fallbacks)

### Objectif
Redimensionner la zone Lieux sur l'onglet 1, gérer les sélecteurs vides par défaut avec fallbacks, interroger l'API Overpass pour les bornes kilométriques (PR) / sorties d'autoroute et charger la couche GeoJSON d'éclairage public.

### Modifications prévues
- Dans `src/components/zones/LieuxZone.jsx` : Agrandir la carte Leaflet et aligner VMA, agglomération et les sélecteurs sur la largeur disponible.
- Mettre à jour les options et l'état des champs pour autoriser la valeur vide `""` par défaut.
- À la soumission de la prédiction dans `App.jsx`, appliquer les fallbacks demandés :
  - Type de voie (`catr`) : `9` ('autre voie')
  - Météo (`atm`) : `1` ('normale')
  - État chaussée (`surf`) : `1` ('normale (sèche)')
  - Régime circulation (`circ`) : `0` ('non renseigné / autre')
  - Aménagement (`infra`) : `0` ('aucun aménagement particulier')
  - Situation sur voie (`situ`) : `8` ('autre situation')
- Dans `src/components/OpenStreetMapViewer.jsx` :
  - Ajouter la fonction de requête Overpass API (`highway=milestone`, `highway=motorway_junction`) à proximité des coordonnées.
  - Formater et afficher la phrase descriptive sous la carte : "Sinistre situé entre borne X et borne Y de l'autoroute X (Sortie N)...".
  - Intégrer un calque `L.geoJSON()` léger pour valider la présence d'éclairage public et mettre à jour le mode d'éclairage.

### Fichiers potentiellement concernés
- `interface/src/components/zones/LieuxZone.jsx`
- `interface/src/components/OpenStreetMapViewer.jsx`
- `interface/src/services/locationService.js` (ou directement dans `OpenStreetMapViewer.jsx`)
- `interface/src/App.jsx`

### Validation prévue
- Vérification du rendu visuel élargi sur l'onglet 1.
- Test d'un clic sur autoroute/route pour vérifier l'affichage des bornes PR et sorties.
- Vérification de la transmission des fallbacks par défaut au moteur de prédiction.

### Message de commit proposé
`feat(interface): enlarge location map, add Overpass PR lookup and empty field fallbacks`

---

## Étape 4 — Zone Véhicules & Chocs 3D (3+ Véhicules, Sub-collision & Duplication B)

### Objectif
Agrandir les modélisateurs 3D sur l'onglet 2, gérer la sélection 3+ véhicules avec type de collision spécifique, ajuster les valeurs par défaut et dupliquer motorisation, manœuvre et obstacle mobile pour le Véhicule B.

### Modifications prévues
- Dans `src/components/zones/VehiculesZone.jsx` :
  - Agrandir le conteneur des modélisateurs 3D.
  - Lorsque `nb_vehicules >= 3`, afficher le sous-menu avec le choix entre 'Carambolage (série de chocs successifs)' (`col = 4`) et 'Accident en accordéon (collisions par l'arrière suite à un ralentissement)' (`col = 5`).
  - Définir les valeurs par défaut : motorisation (`0`), manœuvre (`0`), obstacle mobile (`1` si >=2 véhicules, `4` si 1 seul véhicule).
  - Quand 2+ véhicules sont présents, afficher les sélecteurs de motorisation (`motor_b`), manœuvre (`manv_b`), et obstacle mobile (`macro_obsm_code_b`) pour le Véhicule B.

### Fichiers potentiellement concernés
- `interface/src/components/zones/VehiculesZone.jsx`
- `interface/src/config/constants.js`
- `interface/src/App.jsx`

### Validation prévue
- Basculer entre 1, 2 et 3+ véhicules et valider le sous-menu de collision et la duplication des sélecteurs pour le véhicule B.

### Message de commit proposé
`feat(interface): add multi-vehicle collision options and duplicate controls for vehicle B`

---

## Étape 5 — Zone Usagers & Victimes (Jusqu'à 5 Victimes & Titres Épurés)

### Objectif
Permettre la saisie dynamique de 1 à 5 victimes en fonction du nombre estimé de blessés, fixer le rôle par défaut à 'conducteur' et épuré les titres ("Victime 1", "Victime 2", ...).

### Modifications prévues
- Dans `src/components/zones/UsagersZone.jsx` :
  - Permettre l'incrémentation du nombre de victimes de 1 jusqu'à 5 (max 5).
  - Générer dynamiquement les sous-formulaires pour Victime 1, 2, 3, 4, 5.
  - Définir le rôle par défaut (`catu`) à `1` ('conducteur').
  - Remplacer les titres contenant "(principale)" ou "(secondaire)" par "Victime X".

### Fichiers potentiellement concernés
- `interface/src/components/zones/UsagersZone.jsx`
- `interface/src/App.jsx`

### Validation prévue
- Ajuster le nombre de blessés à 1, 3 et 5, et vérifier que 1, 3 et 5 fiches victimes s'affichent correctement sans mention principale/secondaire.

### Message de commit proposé
`feat(interface): support up to 5 victims with cleaned titles and default driver role`

---

## Étape 6 — Validation Globale & Documentation

### Objectif
S'assurer du bon fonctionnement global de l'application React Vite, tester la prédiction bout-en-bout, valider les règles de style et générer le journal des modifications dans `docs/changes/2026-09-14_interface/changes.md`.

### Modifications prévues
- Tester la compilation et l'exécution sans erreur.
- Rédiger le fichier `docs/changes/2026-09-14_interface/changes.md` en français.

### Fichiers potentiellement concernés
- `docs/changes/2026-09-14_interface/changes.md`

### Validation prévue
- Exécution de `npm run build` dans `interface`.

### Message de commit proposé
`docs(interface): add change log for UI redesign and spatial features`

---

## Critères de fin

- L'interface s'affiche avec 2 onglets "Principal" et "Détails".
- Le bouton "Envoyer" et la carte de prédiction sont fixes et visibles sur les 2 onglets.
- Les zones Caractéristiques et Lieux sont adaptées sur l'onglet 1 (période auto, bornes PR, fallbacks).
- Les zones Véhicules et Usagers sont adaptées sur l'onglet 2 (modélisateurs 3D agrandis, 3+ véhicules, jusqu'à 5 victimes).
- Le bloc inutile des métadonnées de prédiction a été retiré.
- `npm run build` et `npm run dev` s'exécutent avec succès.
