#!/bin/sh
set -eu

for directory in \
    "$BENTOML_HOME" \
    "$BENTOML_HOME/models" \
    "$BENTOML_HOME/bentos" \
    "$BENTOML_HOME/envs" \
    "$BENTOML_HOME/tmp"
do
    mkdir -p "$directory"
    chown app "$directory"
done

# Répare les stores créés par une ancienne image dont l'utilisateur `app`
# utilisait un autre UID. Les permissions BentoML peuvent être volontairement
# restrictives : harmoniser le propriétaire suffit, sans les élargir.
chown -R app "$BENTOML_HOME/models"

exec runuser -u app -- "$@"
