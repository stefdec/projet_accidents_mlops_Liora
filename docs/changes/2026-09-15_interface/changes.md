## Support des équipements de sécurité multiples (secu1, secu2, secu3) et simulation GeoJSON de l'éclairage public

**Message de commit**

`feat(interface): add secu1-3 choices per victim and time-dependent geojson lighting simulation`

**Ce qui a changé**

- **Zone Usagers & Victimes** : Ajout de 3 menus déroulants d'équipements de sécurité (`secu1`, `secu2`, `secu3`) pour chaque fiche de victime (Victime 1 à Victime 6) conformément aux standards de variables BAAC.
- **Zone Lieux & Environnement** : Intégration d'une simulation automatique d'éclairage public sur le calque GeoJSON native Leaflet `L.geoJSON()`. La simulation est conditionnée par l'horodatage du sinistre (pas de tirage aléatoire en journée entre 06h et 18h ; tirage aléatoire des modalités 3, 4, 5 la nuit/soirée).
- **Documentation** : Mise à jour du document technique `interface/rapport.md`.

**Pourquoi**

- Permettre à l'opérateur de saisir plusieurs équipements de sécurité (ex. ceinture + airbag, ou casque + gants) en adéquation exacte avec les champs `secu1`, `secu2`, `secu3` du modèle MLOps.
- Fournir une démonstration interactive de l'intégration GeoJSON pour l'éclairage public nocturne sur la carte Leaflet.

**Fichiers**

- `interface/src/App.jsx`
- `interface/src/components/zones/LieuxZone.jsx`
- `interface/src/components/OpenStreetMapViewer.jsx`
- `interface/src/components/zones/UsagersZone.jsx`
- `interface/rapport.md`
- `docs/changes/2026-09-15_interface/changes.md`

**Validation**

- Compilation `npm run build` exécutée avec succès (0 erreur de compilation, 1524 modules transformés).
