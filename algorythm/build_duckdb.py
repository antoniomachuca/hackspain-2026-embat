"""
Pipeline de Ingesta y Creación de xray.duckdb.

Carga datos desde:
  - dataset/companies.csv
  - dataset/transactions.csv (2.55M registros)
  - dataset/invoices.csv (897k registros)
  - dataset/balances.csv
  - dataset/groups.csv
  - algorythm/engine_results/scores_monthly.csv
  - algorythm/engine_results/alerts_history.json & alerts_feed.json

Crea tablas optimizadas con tipos nativos e índices para consultas analíticas ultra-rápidas (<5 ms).
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "xray.duckdb"
DATA_DIR = ROOT / "dataset"
RESULTS_DIR = ROOT / "algorythm" / "engine_results"


def build_database(db_path: Optional[Path] = None, rebuild: bool = True, verbose: bool = True) -> Path:
    target_db = Path(db_path) if db_path else DEFAULT_DB_PATH
    start_time = time.time()

    if verbose:
        print(f"=== Construyendo base de datos DuckDB: {target_db.name} ===")
        print(f"Ruta de destino: {target_db}")

    # Si se pide rebuild y la base existe, la eliminamos de forma segura para garantizar idempotencia
    if rebuild and target_db.exists():
        if verbose:
            print("Eliminando base de datos anterior para regeneración limpia...")
        try:
            target_db.unlink()
            wal_file = target_db.with_name(target_db.name + ".wal")
            if wal_file.exists():
                wal_file.unlink()
        except Exception as e:
            if verbose:
                print(f"Advertencia al limpiar base anterior: {e}")

    con = duckdb.connect(str(target_db))

    try:
        # Configuración para optimizar memoria y paralelismo en Mac/Linux
        con.execute("PRAGMA threads=4;")
        con.execute("PRAGMA preserve_insertion_order=false;")

        # -------------------------------------------------------------
        # 1. Tabla 'companies'
        # -------------------------------------------------------------
        t0 = time.time()
        companies_csv = DATA_DIR / "companies.csv"
        if not companies_csv.exists():
            raise FileNotFoundError(f"No se encontró {companies_csv}")

        con.execute(f"""
            CREATE OR REPLACE TABLE companies AS 
            SELECT 
                company_id,
                group_id,
                country,
                currency,
                erp,
                (erp IS NOT NULL AND erp != '') AS has_erp,
                TRY_CAST(created_at AS TIMESTAMP) AS created_at
            FROM read_csv_auto('{companies_csv}');
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_companies_group ON companies(group_id);")
        count_companies = con.execute("SELECT count(*) FROM companies;").fetchone()[0]
        if verbose:
            print(f"✓ Tabla 'companies' creada: {count_companies:,} empresas ({time.time() - t0:.2f}s)")

        # -------------------------------------------------------------
        # 2. Tabla 'groups'
        # -------------------------------------------------------------
        groups_csv = DATA_DIR / "groups.csv"
        if groups_csv.exists():
            con.execute(f"""
                CREATE OR REPLACE TABLE groups AS 
                SELECT 
                    group_id,
                    erp,
                    n_companies_in_sample
                FROM read_csv_auto('{groups_csv}');
            """)
            if verbose:
                print("✓ Tabla 'groups' creada.")

        # -------------------------------------------------------------
        # 3. Tabla 'company_scores'
        # -------------------------------------------------------------
        t0 = time.time()
        scores_csv = RESULTS_DIR / "scores_monthly.csv"
        if not scores_csv.exists():
            raise FileNotFoundError(f"No se encontró {scores_csv}. Ejecute antes algorythm/calc_score.py si no está generado.")

        con.execute(f"""
            CREATE OR REPLACE TABLE company_scores AS 
            SELECT 
                company_id,
                group_id,
                currency,
                TRY_CAST(as_of AS DATE) AS as_of,
                CAST(score AS DOUBLE) AS score,
                CAST(base_health AS DOUBLE) AS base_health,
                L, L_bank, C, C_bank, D,
                CAST(momentum AS DOUBLE) AS momentum,
                growth_quality, fragility,
                CAST(liquidity_points AS DOUBLE) AS liquidity_points,
                CAST(collections_points AS DOUBLE) AS collections_points,
                CAST(debt_points AS DOUBLE) AS debt_points,
                CAST(momentum_points AS DOUBLE) AS momentum_points,
                CAST(growth_points AS DOUBLE) AS growth_points,
                CAST(fragility_points AS DOUBLE) AS fragility_points,
                CAST(clipping_points AS DOUBLE) AS clipping_points,
                raw_score,
                data_confidence_index,
                state,
                state_eligible,
                health_band
            FROM read_csv_auto('{scores_csv}');
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_scores_as_of ON company_scores(as_of);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_scores_state ON company_scores(state);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_scores_comp ON company_scores(company_id);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_scores_comp_asof ON company_scores(company_id, as_of);")
        count_scores = con.execute("SELECT count(*) FROM company_scores;").fetchone()[0]
        if verbose:
            print(f"✓ Tabla 'company_scores' creada: {count_scores:,} registros ({time.time() - t0:.2f}s)")

        # -------------------------------------------------------------
        # 4. Tabla 'transactions' (~2,55M filas)
        # -------------------------------------------------------------
        t0 = time.time()
        transactions_csv = DATA_DIR / "transactions.csv"
        if transactions_csv.exists():
            con.execute(f"""
                CREATE OR REPLACE TABLE transactions AS 
                SELECT 
                    transaction_id,
                    company_id,
                    product_id,
                    TRY_CAST(date AS DATE) AS date,
                    TRY_CAST(value_date AS DATE) AS value_date,
                    CAST(amount AS DOUBLE) AS amount,
                    CAST(exchange_rate AS DOUBLE) AS exchange_rate,
                    status,
                    accounting_status,
                    category,
                    description,
                    counterparty_id
                FROM read_csv_auto('{transactions_csv}');
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_trans_comp_date ON transactions(company_id, date);")
            con.execute("CREATE INDEX IF NOT EXISTS idx_trans_comp ON transactions(company_id);")
            count_trans = con.execute("SELECT count(*) FROM transactions;").fetchone()[0]
            if verbose:
                print(f"✓ Tabla 'transactions' creada: {count_trans:,} transacciones ({time.time() - t0:.2f}s)")
        else:
            if verbose:
                print("⚠ Advertencia: transactions.csv no encontrado. Se omite.")

        # -------------------------------------------------------------
        # 5. Tabla 'invoices' (~897k filas)
        # -------------------------------------------------------------
        t0 = time.time()
        invoices_csv = DATA_DIR / "invoices.csv"
        if invoices_csv.exists():
            con.execute(f"""
                CREATE OR REPLACE TABLE invoices AS 
                SELECT 
                    operation_id AS invoice_id,
                    company_id,
                    document_type,
                    TRY_CAST(issuance_date AS DATE) AS issue_date,
                    TRY_CAST(due_date AS DATE) AS due_date,
                    TRY_CAST(payment_date AS DATE) AS paid_date,
                    CAST(amount AS DOUBLE) AS total_amount,
                    CAST(pending_amount AS DOUBLE) AS pending_amount,
                    currency,
                    accounting_currency,
                    CAST(exchange_rate AS DOUBLE) AS exchange_rate,
                    status,
                    concept,
                    counterparty_id
                FROM read_csv_auto('{invoices_csv}');
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_invoices_comp_due ON invoices(company_id, due_date);")
            con.execute("CREATE INDEX IF NOT EXISTS idx_invoices_comp ON invoices(company_id);")
            con.execute("CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);")
            count_inv = con.execute("SELECT count(*) FROM invoices;").fetchone()[0]
            if verbose:
                print(f"✓ Tabla 'invoices' creada: {count_inv:,} facturas ({time.time() - t0:.2f}s)")
        else:
            if verbose:
                print("⚠ Advertencia: invoices.csv no encontrado. Se omite.")

        # -------------------------------------------------------------
        # 6. Tabla 'balances'
        # -------------------------------------------------------------
        balances_csv = DATA_DIR / "balances.csv"
        if balances_csv.exists():
            con.execute(f"""
                CREATE OR REPLACE TABLE balances AS 
                SELECT 
                    product_id,
                    company_id,
                    TRY_CAST(date AS DATE) AS date,
                    CAST(balance AS DOUBLE) AS balance,
                    CAST(available AS DOUBLE) AS available,
                    CAST(granted AS DOUBLE) AS granted,
                    CAST(liquidity AS DOUBLE) AS liquidity,
                    CAST(countable AS DOUBLE) AS countable
                FROM read_csv_auto('{balances_csv}');
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_balances_comp ON balances(company_id);")
            if verbose:
                print("✓ Tabla 'balances' creada.")

        # -------------------------------------------------------------
        # 7. Tabla 'alerts' (Carga de JSON histórico y snapshot activo)
        # -------------------------------------------------------------
        t0 = time.time()
        con.execute("""
            CREATE OR REPLACE TABLE alerts (
                alert_id VARCHAR PRIMARY KEY,
                company_id VARCHAR NOT NULL,
                group_id VARCHAR NOT NULL,
                as_of DATE NOT NULL,
                state VARCHAR NOT NULL,
                severity VARCHAR NOT NULL,
                direction VARCHAR NOT NULL,
                score DOUBLE NOT NULL,
                delta_score DOUBLE NOT NULL,
                momentum DOUBLE NOT NULL,
                drivers_json JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        alerts_map = {}
        # Cargar alertas históricas
        hist_file = RESULTS_DIR / "alerts_history.json"
        if hist_file.exists():
            with hist_file.open(encoding="utf-8") as f:
                data = json.load(f)
                alert_list = data.get("alerts", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                for a in alert_list:
                    if isinstance(a, dict) and "alert_id" in a:
                        alerts_map[a["alert_id"]] = a

        # Cargar alertas del feed (snapshot actual)
        feed_file = RESULTS_DIR / "alerts_feed.json"
        if feed_file.exists():
            with feed_file.open(encoding="utf-8") as f:
                data = json.load(f)
                alert_list = data.get("alerts", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                for a in alert_list:
                    if isinstance(a, dict) and "alert_id" in a:
                        alerts_map[a["alert_id"]] = a

        if alerts_map:
            rows = [
                (
                    a["alert_id"],
                    a["company_id"],
                    a.get("group_id", ""),
                    a["as_of"],
                    a.get("state", "ESTABLE"),
                    a.get("severity", "INFORMATIVA"),
                    a.get("direction", "neutral"),
                    float(a.get("score", 0.0)),
                    float(a.get("delta_score", 0.0)),
                    float(a.get("momentum", 0.0)),
                    json.dumps(a.get("drivers", []))
                )
                for a in alerts_map.values()
            ]
            con.executemany("""
                INSERT INTO alerts (
                    alert_id, company_id, group_id, as_of, state, severity, direction, score, delta_score, momentum, drivers_json
                ) VALUES (?, ?, ?, TRY_CAST(? AS DATE), ?, ?, ?, ?, ?, ?, ?);
            """, rows)

        con.execute("CREATE INDEX IF NOT EXISTS idx_alerts_date ON alerts(as_of);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_alerts_comp ON alerts(company_id);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_alerts_sev ON alerts(severity);")
        count_alerts = con.execute("SELECT count(*) FROM alerts;").fetchone()[0]
        if verbose:
            print(f"✓ Tabla 'alerts' creada: {count_alerts:,} alertas ({time.time() - t0:.2f}s)")

        # -------------------------------------------------------------
        # 8. Vista Analítica de Último Corte con Delta 3M
        # -------------------------------------------------------------
        con.execute("""
            CREATE OR REPLACE VIEW v_latest_company_scores AS
            WITH scored AS (
                SELECT 
                    *,
                    LAG(score, 3) OVER (PARTITION BY company_id ORDER BY as_of ASC) AS score_3m_ago
                FROM company_scores
            )
            SELECT 
                c.company_id,
                c.group_id,
                c.country,
                c.currency,
                c.erp,
                c.has_erp,
                c.created_at AS company_created_at,
                s.as_of,
                s.score,
                s.base_health,
                s.state,
                s.momentum,
                ROUND(s.score - COALESCE(s.score_3m_ago, s.score), 2) AS delta_3m,
                s.health_band,
                s.data_confidence_index,
                s.state_eligible,
                s.liquidity_points,
                s.collections_points,
                s.debt_points,
                s.momentum_points,
                s.growth_points,
                s.fragility_points,
                s.clipping_points
            FROM companies c
            JOIN scored s ON c.company_id = s.company_id
            WHERE s.as_of = (SELECT MAX(as_of) FROM company_scores);
        """)
        if verbose:
            print("✓ Vista analítica 'v_latest_company_scores' creada.")

    finally:
        con.close()

    total_time = time.time() - start_time
    if verbose:
        db_size_mb = target_db.stat().st_size / (1024 * 1024)
        print(f"\n=======================================================")
        print(f"✓ Base de datos {target_db.name} ({db_size_mb:.1f} MB) generada con éxito en {total_time:.2f}s.")
        print(f"=======================================================")

    return target_db


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Construir base de datos DuckDB para X-Ray")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Ruta del archivo DuckDB")
    parser.add_argument("--no-rebuild", action="store_true", help="No eliminar la base si ya existe")
    parser.add_argument("--quiet", action="store_true", help="Silenciar salida informativa")
    args = parser.parse_args()

    build_database(
        db_path=args.db_path,
        rebuild=not args.no_rebuild,
        verbose=not args.quiet
    )
