"""Siembra el volumen /data con los ficheros pesados que no viajan en git.

El motor necesita dos cosas que están en .gitignore:
  - xray.duckdb            (la Fuente Única de Verdad que sirve la API)
  - dataset/*.csv          (los CSV crudos que load_bank_panel recorre para
                            la previsión estructural)

Ambos viven en un bucket privado de Railway. Este script los baja al volumen
la primera vez y en los arranques siguientes no hace nada: compara el tamaño
del objeto con el del fichero local y se salta los que ya cuadran.
"""

import os
import sys
from pathlib import Path

OBJETOS = (
    "xray.duckdb",
    "dataset/companies.csv",
    "dataset/transactions.csv",
    "dataset/invoices.csv",
    "dataset/balances.csv",
    "dataset/groups.csv",
    "dataset/banking_products.csv",
    "dataset/debt_products.csv",
    "dataset/debt_schedule_config.csv",
)


def cliente():
    import boto3
    from botocore.config import Config

    faltan = [v for v in ("XRAY_S3_ENDPOINT", "XRAY_S3_BUCKET", "XRAY_S3_ACCESS_KEY_ID",
                          "XRAY_S3_SECRET_ACCESS_KEY") if not os.environ.get(v)]
    if faltan:
        raise SystemExit(f"Faltan variables del bucket: {', '.join(faltan)}")

    return boto3.client(
        "s3",
        endpoint_url=os.environ["XRAY_S3_ENDPOINT"],
        aws_access_key_id=os.environ["XRAY_S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["XRAY_S3_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("XRAY_S3_REGION", "us-east-1"),
        config=Config(s3={"addressing_style": os.environ.get("XRAY_S3_ADDRESSING", "virtual")}, retries={"max_attempts": 5, "mode": "standard"}),
    )


def main() -> int:
    destino = Path(os.environ.get("XRAY_DATA_DIR", "/data"))
    destino.mkdir(parents=True, exist_ok=True)

    s3 = cliente()
    bucket = os.environ["XRAY_S3_BUCKET"]
    prefijo = os.environ.get("XRAY_S3_PREFIX", "").strip("/")

    for nombre in OBJETOS:
        clave = f"{prefijo}/{nombre}" if prefijo else nombre
        local = destino / nombre
        local.parent.mkdir(parents=True, exist_ok=True)

        remoto = s3.head_object(Bucket=bucket, Key=clave)["ContentLength"]
        if local.exists() and local.stat().st_size == remoto:
            print(f"[seed] ya está  {nombre} ({remoto/1e6:.1f} MB)", flush=True)
            continue

        print(f"[seed] bajando {nombre} ({remoto/1e6:.1f} MB)...", flush=True)
        parcial = local.with_suffix(local.suffix + ".parcial")
        s3.download_file(bucket, clave, str(parcial))
        parcial.replace(local)
        print(f"[seed] listo    {nombre}", flush=True)

    # El .wal de una copia interrumpida deja el DuckDB ilegible en read_only.
    wal = destino / "xray.duckdb.wal"
    if wal.exists():
        wal.unlink()

    return 0


if __name__ == "__main__":
    sys.exit(main())
