# Monitoring de la stack

```text
train-api → JSON drift/ML et CSV carbone → trois exporters → Prometheus → Grafana
predict-api → /metrics → Prometheus
node-exporter / cAdvisor → Prometheus
logs des quatre API → Alloy → Loki → Grafana
```

Les exporters partagent une image minimale avec le groupe exporters de uv.lock : FastAPI, uvicorn, pandas, prometheus-client. Aucun modèle, DVC ou code frontend n’est installé dans cette image. Les fichiers runtime sont montés en lecture seule ; train-api les produit.

| Cible Prometheus | Source | Donnée |
| --- | --- | --- |
| predict_api | predict-api:8000/metrics | Requêtes, erreurs, latence, classes, modèle chargé |
| drift_monitoring | drift-exporter:8001/metrics | monitoring/drift/drift_results.json |
| ml_monitoring | ml-exporter:8003/metrics | monitoring/ml/model_performance.json |
| sustainability | sustainability-exporter:8002/metrics | reports/carbon/emissions.csv |
| node_exporter | node-exporter:9100 | Ressources hôte |
| cadvisor | cadvisor:8080 | Ressources Docker, selon compatibilité du runtime |

```bash
make monitoring-up
make stack-status
make monitoring-down
```

Prometheus : http://localhost:9090 ; Grafana : http://localhost:3000. Les configs/dashboards sont sous monitoring/prometheus et monitoring/grafana. L’accès Grafana suit les comptes locaux de l’installation ; aucun credential réel n’est stocké dans ces guides.

Alloy utilise le socket Docker en lecture seule pour sélectionner les conteneurs portant org.accidents.stack=api. Loki conserve leurs flux avec project=accidents-mlops et service=auth-api/pull-data-api/train-api/predict-api. Les anciens labels restent dans le stockage historique conservé.

Exemple Explore : `{project="accidents-mlops", service="train-api"}`. Vérifier les flux récents, pas seulement /ready. Voir [Alloy/Loki](docs/operations/logs-loki-alloy.md).

Les alertes Grafana et le contact Slack sont provisionnés depuis les fichiers YAML ; GF_SLACK_WEBHOOK est local. La livraison Slack n’est pas validée par les tests de nettoyage.

Sur le Docker Desktop/overlayfs testé, cAdvisor répond et accède au daemon, mais les séries CPU/mémoire par conteneur nommé restent absentes. La cible up seule ne valide pas ces panneaux. Détails et essais : [validation locale](docs/operations/local-validation.md). Les métriques API/exporters/node restent accessibles.

stack-down et monitoring-down conservent les volumes. reset conserve les volumes monitoring ; reset-full les supprime. Les sorties JSON/CSV sont des données runtime, distinctes du code et ignorées lorsque prévu.
