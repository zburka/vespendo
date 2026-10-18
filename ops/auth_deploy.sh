#!/bin/bash
# A belépési kapu (vespendo-auth) építése és (újra)indítása. A titkok a /root/.vespendo-auth.env fájlban vannak (nincs a repóban).
set -euo pipefail
cd "$(dirname "$0")/.."
ENVF=/root/.vespendo-auth.env
if [ ! -f "$ENVF" ]; then
  source /root/.vespendo.env
  TABLAK=$(python3 -c "import json;print(json.dumps(json.load(open('ops/ids.json'))['tablak']))")
  umask 077
  cat > "$ENVF" <<EOT
AUTH_DB=/data/auth.db
AUTH_JWT_TITOK=$(openssl rand -hex 32)
REGISZTRACIOS_KOD=$(openssl rand -hex 6)
N8N_URL=http://n8n:5678
N8N_UT_ELOTAG=${N8N_UT_ELOTAG:-h-}
N8N_BELSO_KULCS=${VESPENDO_APP_KEY}
BASEROW_URL=${BASEROW_URL}
BASEROW_TOKEN=${BASEROW_VESPENDO_TOKEN}
BASEROW_TABLAK=${TABLAK}
EOT
fi
docker build -q -t vespendo-auth:latest auth-service
mkdir -p /root/vespendo-auth-data && chown 10001 /root/vespendo-auth-data
docker rm -f vespendo-auth >/dev/null 2>&1 || true
docker run -d --name vespendo-auth --restart unless-stopped --network cloudoptima-net \
  --env-file "$ENVF" -v /root/vespendo-auth-data:/data --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges \
  vespendo-auth:latest >/dev/null
sleep 3
docker exec vespendo-auth python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/api/health').read())"
