#!/usr/bin/env sh
# Arranque del servicio "api": siembra el volumen, engancha las rutas que el
# código espera en la raíz del repo, y levanta uvicorn.
set -e

DATA_DIR="${XRAY_DATA_DIR:-/data}"

python -m deploy.seed_data

# El backend busca xray.duckdb y dataset/ en la raíz del repo
# (backend/database.py y forecasting/benchmark.py:default_dataset). En vez de
# tocar esas rutas, las apuntamos al volumen con enlaces simbólicos.
ln -sfn "$DATA_DIR/xray.duckdb" /app/xray.duckdb
ln -sfn "$DATA_DIR/dataset" /app/dataset

PUERTO="${PORT:-8000}"

# Precalentado: la primera previsión estructural recorre transactions.csv
# entero (2,5 M filas) en Python. Si la dispara un visitante, se come el
# minuto largo esperando. Lo disparamos nosotros contra el propio servidor
# para que el caché de load_company_banks ya esté caliente en la demo.
if [ "${XRAY_WARMUP:-1}" = "1" ]; then
  (
    until curl -sf "http://127.0.0.1:${PUERTO}/api/health" >/dev/null 2>&1; do sleep 2; done
    echo "[warmup] cargando el panel bancario..."
    curl -sf -o /dev/null "http://127.0.0.1:${PUERTO}/api/companies/COMP_0001/prevision-estructural" || true
    echo "[warmup] panel bancario listo"
  ) &
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port "$PUERTO" --workers 1
