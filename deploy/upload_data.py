"""Sube al bucket de Railway los ficheros pesados que no están en git.

Se ejecuta desde tu máquina, una sola vez (y cada vez que regeneres el
DuckDB), con las credenciales que inyecta el CLI de Railway:

    railway run --service api python -m deploy.upload_data

Así las claves del bucket nunca se copian a mano ni acaban en un fichero.
Sube en multipart y salta lo que ya está arriba con el mismo tamaño.
"""

import os
import sys
from pathlib import Path

from deploy.seed_data import OBJETOS, cliente

RAIZ = Path(__file__).resolve().parents[1]


def main() -> int:
    from boto3.s3.transfer import TransferConfig
    from botocore.exceptions import ClientError

    s3 = cliente()
    bucket = os.environ["XRAY_S3_BUCKET"]
    prefijo = os.environ.get("XRAY_S3_PREFIX", "").strip("/")
    transfer = TransferConfig(multipart_threshold=64 * 1024 * 1024,
                              multipart_chunksize=64 * 1024 * 1024,
                              max_concurrency=4)

    faltan = [n for n in OBJETOS if not (RAIZ / n).exists()]
    if faltan:
        print("No encuentro estos ficheros en local:", ", ".join(faltan), file=sys.stderr)
        print("Genera el DuckDB con: python algorithm/build_duckdb.py", file=sys.stderr)
        return 1

    for nombre in OBJETOS:
        local = RAIZ / nombre
        clave = f"{prefijo}/{nombre}" if prefijo else nombre
        tam = local.stat().st_size

        try:
            if s3.head_object(Bucket=bucket, Key=clave)["ContentLength"] == tam:
                print(f"[subida] ya está  {nombre} ({tam/1e6:.1f} MB)")
                continue
        except ClientError:
            pass

        print(f"[subida] subiendo {nombre} ({tam/1e6:.1f} MB)...", flush=True)
        s3.upload_file(str(local), bucket, clave, Config=transfer)
        print(f"[subida] listo    {nombre}")

    print("\nDatos en el bucket. Redespliega el servicio api para que los siembre.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
