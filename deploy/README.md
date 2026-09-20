# Despliegue en Railway

Proyecto `xray-embat`, entorno `production`. Dos servicios y nada más:
DuckDB va embebido en la API, así que no hay servicio de base de datos.

```
xray-embat
├── api   Dockerfile (python 3.12) · uvicorn backend.main:app
│         volumen /data  ←  bucket "xray-data" (siembra al arrancar)
│         https://api-production-7fab.up.railway.app
└── web   front/ · nixpacks · next build / next start
          https://web-production-27da6.up.railway.app
```

## Por qué un bucket y un volumen

`xray.duckdb` (~400 MB) y `dataset/*.csv` (~650 MB) están en `.gitignore`, así
que la imagen no puede traerlos. Viven en un bucket privado de Railway;
`deploy/entrypoint.sh` ejecuta `deploy/seed_data.py`, que los baja al volumen
`/data` la primera vez y los salta en arranques posteriores comparando tamaños.
Luego enlaza `/data/xray.duckdb` y `/data/dataset` a la raíz de la app, que es
donde `backend/database.py` y `forecasting/benchmark.py` los buscan — así no
hubo que tocar ninguna ruta del motor.

Los CSV crudos hacen falta además del DuckDB: `forecasting/structural.py` llama
a `load_bank_panel()` sobre `transactions.csv` para la previsión estructural.

## Subir o refrescar los datos

Desde tu máquina, con el DuckDB ya construido (`python algorithm/build_duckdb.py`):

```bash
railway link            # proyecto xray-embat, entorno production
railway run --service api python -m deploy.upload_data
```

`railway run` inyecta las credenciales del bucket, así que no hay que copiar
ninguna clave. Después, redespliega `api` para que siembre el volumen.

## Variables

| Servicio | Variable | Valor |
| --- | --- | --- |
| api | `XRAY_S3_*` | referencias a `xray-data` (BUCKET, ENDPOINT, ACCESS_KEY_ID, SECRET_ACCESS_KEY, REGION) |
| api | `XRAY_DATA_DIR` | `/data` |
| api | `XRAY_WARMUP` | `1` — precarga el panel bancario al arrancar |
| web | `NEXT_PUBLIC_API_URL` | dominio público de `api` |
| web | `OPENAI_API_KEY` | clave de OpenAI para el asistente (`/agente`). Solo la lee el servidor de Next |
| web | `OPENAI_MODEL` | modelo del asistente; si falta, `gpt-5-mini` |
| web | `XRAY_API_URL` | base de la API vista desde el servidor de Next (puede ser la red privada de Railway). Si falta, usa `NEXT_PUBLIC_API_URL` |

`NEXT_PUBLIC_API_URL` se inlinea en el bundle **en build**: si cambia el dominio
de la API hay que redesplegar el front, no basta con reiniciarlo.

## Lo que queda fuera

`/api/forecasts/*` (los endpoints de laboratorio) leen `forecasting/artifacts/`,
que no está versionado: devuelven 503 hasta que se generen y se suban. El
producto —cartera, ficha, what-if, previsión estructural— no depende de ellos.
