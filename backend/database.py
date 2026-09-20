"""
Módulo de acceso y conexión a DuckDB para X-Ray Backend.

Mantiene una conexión optimizada de sólo lectura (read_only=True) para
concurrencia total en endpoints analíticos de FastAPI.
"""

from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "xray.duckdb"

_shared_connection: Optional[duckdb.DuckDBPyConnection] = None


def get_db_connection() -> duckdb.DuckDBPyConnection:
    """Devuelve la conexión compartida en modo lectura, construyendo la BD si no existe."""
    global _shared_connection
    if _shared_connection is None:
        if not DB_PATH.exists():
            from algorithm.build_duckdb import build_database
            build_database(db_path=DB_PATH, verbose=False)

        _shared_connection = duckdb.connect(str(DB_PATH), read_only=True)
    return _shared_connection


def close_db_connection() -> None:
    """Cierra la conexión compartida a la base de datos."""
    global _shared_connection
    if _shared_connection is not None:
        try:
            _shared_connection.close()
        except Exception:
            pass
        _shared_connection = None


@contextmanager
def get_cursor() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Generador de contexto para obtener un cursor aislado y seguro entre hilos."""
    con = get_db_connection()
    cur = con.cursor()
    try:
        yield cur
    finally:
        cur.close()


def query_dicts(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Ejecuta una consulta SQL y devuelve las filas mapeadas como lista de diccionarios."""
    with get_cursor() as cur:
        res = cur.execute(sql, params)
        cols = [desc[0] for desc in res.description]
        rows = res.fetchall()
        return [dict(zip(cols, row)) for row in rows]


def query_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """Ejecuta una consulta SQL y devuelve la primera fila como diccionario o None."""
    rows = query_dicts(sql, params)
    return rows[0] if rows else None


def normalize_company_id(raw_id: str) -> str:
    """Normaliza identificadores de empresa: '10' -> 'COMP_0010', 'comp_10' -> 'COMP_0010'."""
    val = raw_id.strip().upper()
    if val.startswith("COMP_"):
        return val
    if val.startswith("COMP") and val[4:].isdigit():
        num_str = val[4:].zfill(4)
        return f"COMP_{num_str}"
    if val.isdigit():
        num_str = val.zfill(4)
        return f"COMP_{num_str}"
    return val
