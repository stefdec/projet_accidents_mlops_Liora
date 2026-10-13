# Smoke test predict-api : récupère un JWT via auth-api (8005) puis POST le
# payload sur /predict (8009). Le corps doit être enveloppé : {"input_data": {...}}.
TOKEN=$(curl -s -X POST localhost:8005/login -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"wonderland","token_type":"login"}' \
  | sed -E 's/.*"access_token":"([^"]+)".*/\1/')

curl -s -w '\n-- HTTP %{http_code} --\n' -X POST localhost:8009/predict \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d @payload.json
# 200 {"prediction":[0|1]} = OK | 503 = pas de modèle chargé | 422 = payload invalide | 401 = token KO