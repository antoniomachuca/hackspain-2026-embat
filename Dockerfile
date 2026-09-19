# Imagen del servicio "api" (FastAPI + DuckDB embebido).
# Los datos pesados (xray.duckdb y dataset/*.csv) NO viajan en la imagen:
# se siembran en el volumen /data al arrancar. Ver deploy/entrypoint.sh.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    XRAY_DATA_DIR=/data

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# boto3 solo lo necesita el sembrado desde el bucket, no el motor.
RUN pip install --no-cache-dir -r requirements.txt boto3

COPY . .
RUN chmod +x deploy/entrypoint.sh

EXPOSE 8000
CMD ["deploy/entrypoint.sh"]
