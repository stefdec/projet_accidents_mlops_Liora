# Grafana — dashboards et alertes

## Responsabilité opérationnelle

Grafana fournit une vue opérateur de la stack active en combinant les métriques
Prometheus et les logs Loki. Les dashboards et règles sont provisionnés depuis
le dépôt afin de conserver une configuration reproductible.

Grafana est exposé sur <http://localhost:3000>.

## Sources de données

Les sources sont provisionnées automatiquement :

| Source | UID | URL interne | Usage |
| --- | --- | --- | --- |
| Prometheus | `prometheus` | `http://prometheus:9090` | Métriques, états et alertes. |
| Loki | `loki` | `http://loki:3100` | Logs des API actives. |

Les définitions se trouvent dans
[`monitoring/grafana/provisioning/datasources/`](../../monitoring/grafana/provisioning/datasources/).
Les URLs sont internes au réseau Docker ; elles ne doivent pas être remplacées
par `localhost` dans les datasources provisionnées.

## Dashboards actifs

Les dashboards sont chargés dans le dossier **Accidents** depuis
[`monitoring/grafana/dashboards/`](../../monitoring/grafana/dashboards/).

| Dashboard | Données principales | Usage |
| --- | --- | --- |
| `predict-api-dashboard` | `up`, requêtes, succès, erreurs, latence, `model_load_state` | Santé et trafic de la prédiction. |
| `api-logs-dashboard` | Loki / LogQL | Recherche des logs des API actives. |
| `drift-dashboard` | Drift global et par feature | Détection de dérive des données. |
| `ml-performance-dashboard` | Accuracy, precision, recall, F1, ROC AUC, PR AUC, matrice de confusion | Performance du champion. |
| `sustainability-dashboard` | CO2, énergie, durée CPU/GPU/RAM | Coût environnemental du training. |

Les dashboards des variantes v1 ne sont pas considérés comme des points
d'entrée du parcours opérationnel v2.

## Alertes provisionnées

Les règles sont définies dans
[`monitoring/grafana/provisioning/alerting/rules.yaml`](../../monitoring/grafana/provisioning/alerting/rules.yaml)
et évaluées chaque minute dans le dossier **Accidents**.

| Alerte | Condition | Sévérité |
| --- | --- | --- |
| Cible monitoring indisponible | `up < 1` pendant 2 minutes | Critical |
| Modèle non chargé | `model_load_state < 1` pendant 5 minutes | Critical |
| Taux d'erreur élevé | erreurs/requêtes `> 10%` pendant 10 minutes | Warning |
| Drift global détecté | `data_drift_detected > 0` pendant 30 minutes | Warning |
| Évaluation ML ancienne | dernière évaluation à plus de 8 jours | Warning |
| Rapport de drift ancien | dernier rapport à plus de 8 jours | Warning |

Les alertes de fraîcheur dépendent des timestamps exposés par les exporters ;
une absence de fichier de résultat doit donc être diagnostiquée comme un
problème de production du monitoring, pas comme une valeur métier nulle.

## Démarrage et accès

```bash
make monitoring-up
open http://localhost:3000
```

Le provisioning est monté en lecture seule depuis le dépôt. Les modifications
durables doivent être faites dans les fichiers JSON/YAML versionnés, puis
rechargées par Grafana.

## Procédure de validation

1. Grafana démarre après Prometheus et son conteneur est healthy.
2. Les sources `prometheus` et `loki` apparaissent avec les bons UID.
3. Le dossier **Accidents** contient les dashboards actuels attendus.
4. Le dashboard de prédiction affiche la cible, le trafic, les erreurs et l'état
   du modèle.
5. Le dashboard de logs retrouve une ligne générée par `/health`.
6. Les dashboards drift, performance ML et soutenabilité affichent une valeur
   lorsque leurs fichiers de résultats sont disponibles.
7. Les six familles d'alertes sont chargées et pointent vers la source correcte.

## Diagnostic

- Source rouge ou indisponible : tester `http://prometheus:9090` ou
  `http://loki:3100` depuis le réseau Docker et vérifier les conteneurs.
- Dashboard vide : vérifier la cible Prometheus, la fraîcheur des exporters et
  la période temporelle sélectionnée.
- Logs absents : consulter la fiche [Alloy / Loki](logs-loki-alloy.md).
- Modèle non chargé : consulter les fiches [predict-api](predict-api.md)
  et [initial-train](initial-training.md).
- Alerte de fraîcheur : vérifier le DAG, les fichiers de résultats et les
  timestamps plutôt que de modifier l'alerte sans diagnostic.

Retour à l'[index du wiki opérationnel](README.md) et à la fiche
[métriques / Prometheus](metrics-prometheus.md).
