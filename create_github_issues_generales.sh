#!/usr/bin/env bash
set -euo pipefail
REPO="${1:?Usage: $0 OWNER/REPO CSV_FILE}"
CSV_FILE="${2:-roadmap_MLOps_accidents_generale_github.csv}"

python3 - "$REPO" "$CSV_FILE" <<'PY'
import csv, subprocess, sys
repo, path = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        body = f"""### Phase
{r['Phase']}

### Description
{r['Description']}

### Planning
- Responsable prévu : {r['Owner']}
- Priorité : {r['Priority']}
- Début : {r['Start date']}
- Deadline : {r['Target date']}
- Estimation : {r['Estimate (days)']} jour(s)
- Dépendances : {r['Dependencies'] or 'Aucune'}

### Livrable
{r['Deliverable']}

### Référence
{r['ID']}
"""
        subprocess.run(
            ["gh","issue","create","--repo",repo,"--title",r["Title"],"--body",body],
            check=True
        )
PY
