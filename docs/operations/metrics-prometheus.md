# Métriques et Prometheus

## Responsabilité opérationnelle

Prometheus collecte périodiquement les métriques exposées par l'API de
prédiction et par les exporters de monitoring. Ces séries alimentent les
dashboards et les règles d'alerte Grafana.

La configuration actuelle utilise un intervalle global de scrape de 30 secondes
et conserve les données pendant 180 jours, avec une limite de taille de 8 Go.

## Cibles configurées

La configuration de référence est
[`monitoring/prometheus/prometheus.yml`](../../monitoring/prometheus/prometheus.yml).

| Job Prometheus | Cible | Chemin | Contenu |
| --- | --- | --- | --- |
| `sustainability` | `sustainability-exporter:8002` | `/metrics` par défaut | Dernier coût énergétique et carbone d'un entraînement. |
| `drift_monitoring` | `drift-exporter:8001` | `/metrics` par défaut | Drift global et drift par feature. |
| `ml_monitoring` | `ml-exporter:8003` | `/metrics` | Performance du champion sur la semaine évaluée. |
| `predict_api` | `predict-api:8000` | `/metrics` | Requêtes, erreurs, latence, prédictions et état du modèle. |

Dans le réseau Docker, les noms de service sont utilisés ; `localhost` ne doit
pas être utilisé entre conteneurs.

Les services `auth-api`, `pull-data-api` et `train-api` n'ont pas de cible
Prometheus dédiée dans la configuration actuelle. Leur santé doit être suivie
par leurs endpoints `/health`, les healthchecks Docker et les logs Alloy/Loki.

## Métriques de l'API de prédiction

Le module [`src/predict_api/metrics.py`](../../src/predict_api/metrics.py)
définit les métriques suivantes :

| Métrique | Type / labels | Signification |
| --- | --- | --- |
| `total_requests_total` | Counter | Nombre de requêtes de prédiction enregistrées. |
| `error_count_total` | Counter, `status_code` | Nombre d'erreurs par statut. |
| `response_time_seconds` | Histogram | Distribution de la latence de prédiction. |
| `prediction_count_total` | Counter | Nombre de prédictions produites. |
| `prediction_success_total` | Counter | Nombre de prédictions réussies. |
| `predicted_class_distribution_total` | Counter, `class_label` | Répartition des classes prédites. |
| `prediction_probabilities` | Histogram | Distribution des probabilités lorsqu'elles sont disponibles. |
| `prediction_model_info` | Gauge, `version` | Version du modèle ayant servi une prédiction. |
| `model_load_state` | Gauge | `1` si un modèle est chargé, sinon `0`. |

Les compteurs sont exposés avec le suffixe Prometheus `_total`. Les requêtes
`/predict` incrémentent les compteurs et l'histogramme de latence ; les erreurs
du middleware d'authentification sont comptabilisées par statut.

Le montage effectif de `/metrics` doit être vérifié dans le runtime BentoML :
`metrics.py` fournit `mount_metrics`, mais le module `service.py` ne l'appelle
pas explicitement. Tant que cette vérification n'est pas faite, la cible
`predict_api` peut être configurée mais rester inaccessible.

## Exporter de drift

Source :
[`monitoring/exporters/drift/drift_metrics.py`](../../monitoring/exporters/drift/drift_metrics.py).

L'exporter relit `monitoring/drift/drift_results.json` à chaque scrape :

- `data_drift_detected` : `1` si la part globale de features en drift atteint
  le seuil, sinon `0` ;
- `drift_share` : part des features détectées en drift ;
- `drifted_features` : nombre de features en drift ;
- `drift_last_run_timestamp_seconds` : date du dernier rapport ;
- `feature_drift_score{feature,method}` : score par feature ;
- `feature_drift_threshold{feature}` : seuil de la feature ;
- `feature_drift_detected{feature}` : indicateur par feature.

`/health` indique si le fichier de résultats existe. L'absence du fichier ne
produit pas d'erreur de scrape, mais laisse les valeurs précédentes ou initiales
inchangées : il faut alors contrôler la fraîcheur avec
`drift_last_run_timestamp_seconds`.

## Exporter de performance ML

Source :
[`monitoring/exporters/ml/ml_metrics.py`](../../monitoring/exporters/ml/ml_metrics.py).

L'exporter relit `monitoring/ml/model_performance.json` et expose :

- `model_accuracy`, `model_precision`, `model_recall`, `model_f1` ;
- `model_roc_auc`, `model_pr_auc` ;
- `model_true_negative`, `model_false_positive`, `model_false_negative`,
  `model_true_positive` ;
- `model_evaluated_week`, `model_evaluated_rows`, `model_threshold` ;
- `model_monitoring_info{version,source,alias}` ;
- `model_eval_last_run_timestamp_seconds`.

`/refresh` recharge manuellement le fichier. `/health` indique la présence du
résultat ; la fraîcheur doit être vérifiée avec la timestamp exposée.

## Exporter de soutenabilité

Source :
[`monitoring/exporters/sustainability/sustain_metrics.py`](../../monitoring/exporters/sustainability/sustain_metrics.py).

L'exporter relit la dernière ligne de `reports/carbon/emissions.csv` et expose :

- `training_co2_kg` ;
- `training_energy_kwh` ;
- `training_duration_seconds` ;
- `training_cpu_energy_kwh` ;
- `training_gpu_energy_kwh` ;
- `training_ram_energy_kwh` ;
- `training_last_run_timestamp_seconds`.

Une absence de fichier ou un fichier vide ne déclenche pas d'erreur HTTP, mais
aucune nouvelle valeur n'est chargée.

## Démarrage et vérification

```bash
make monitoring-up
docker compose --env-file .env \
  -f docker-compose.monitoring.yml ps
```

Vérifier ensuite les endpoints depuis les conteneurs ou leurs ports exposés :

```bash
curl -sS http://localhost:9090/-/healthy
curl -sS http://localhost:9090/api/v1/targets
curl -sS http://localhost:8001/metrics
curl -sS http://localhost:8002/metrics
curl -sS http://localhost:8003/metrics
curl -sS http://localhost:8009/metrics
```

La dernière commande dépend du montage effectif de `/metrics` par
`predict-api`. Les dashboards sont documentés dans [Grafana](grafana.md).

## Procédure de validation

1. La configuration Prometheus est acceptée par Docker Compose.
2. Les quatre jobs apparaissent dans `/api/v1/targets`.
3. Chaque exporter retourne un contenu au format Prometheus.
4. Un nouveau rapport de drift met à jour `drift_last_run_timestamp_seconds`.
5. Une nouvelle évaluation ML met à jour `model_eval_last_run_timestamp_seconds`.
6. Une nouvelle ligne d'émissions met à jour les métriques de soutenabilité.
7. Une prédiction met à jour les compteurs, la latence et l'état du modèle.
8. Les séries restent de faible cardinalité : ne jamais utiliser de JWT,
   payload, identifiant accident ou chemin comme label.
9. Les règles Grafana détectent une cible indisponible, un modèle non chargé,
   un taux d'erreur élevé, un drift global ou un rapport trop ancien.

## Diagnostic

- Cible `DOWN` : vérifier le nom DNS du service, le port interne et le endpoint
  `/metrics`.
- Métrique absente : vérifier le fichier de résultats et son chemin monté dans
  l'exporter.
- Valeur ancienne : comparer la timestamp de dernière exécution avec l'heure
  courante et vérifier le job qui produit le fichier.
- `predict_api` inaccessible : vérifier le montage de `/metrics`, le worker
  BentoML et l'état de chargement du modèle.
- Prometheus inaccessible : vérifier le conteneur, le port 9090 et le fichier de
  configuration monté en lecture seule.

Retour à l'[index du wiki opérationnel](README.md) et à la fiche
[Grafana](grafana.md).
