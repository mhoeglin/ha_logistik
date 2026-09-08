#!/usr/bin/env sh
set -e

# HA add-ons get a persistent /data volume managed by the Supervisor.
export HEIMWMS_DATA_DIR="${HEIMWMS_DATA_DIR:-/data}"
mkdir -p "$HEIMWMS_DATA_DIR"

# Read the add-on option and pass it to the app as an env var. Seeding itself
# happens in the app lifespan (robust; avoids shell-boolean parsing issues).
SEED="false"
if [ -f /data/options.json ]; then
  SEED="$(python3 -c "import json;print('true' if json.load(open('/data/options.json')).get('seed_demo_data') else 'false')" 2>/dev/null || echo false)"
fi
export HEIMWMS_SEED="$SEED"

echo "[heimwms] starting, data dir: $HEIMWMS_DATA_DIR, seed=$HEIMWMS_SEED"
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
