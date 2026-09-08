#!/usr/bin/env sh
set -e

# HA add-ons get a persistent /data volume managed by the Supervisor.
export HEIMWMS_DATA_DIR="${HEIMWMS_DATA_DIR:-/data}"
mkdir -p "$HEIMWMS_DATA_DIR"

# Read add-on options (HA writes them to /data/options.json).
SEED="false"
if [ -f /data/options.json ]; then
  SEED="$(python3 -c "import json;print(str(json.load(open('/data/options.json')).get('seed_demo_data', False)).lower())" 2>/dev/null || echo false)"
fi

if [ "$SEED" = "true" ]; then
  echo "[heimwms] seed_demo_data=true -> Seeding demo data (nur wenn DB leer)."
  python3 -m scripts.seed || echo "[heimwms] Seeding übersprungen/fehlgeschlagen."
fi

echo "[heimwms] starting, data dir: $HEIMWMS_DATA_DIR"
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
