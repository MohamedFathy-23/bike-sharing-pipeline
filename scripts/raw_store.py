"""Steps 2 and 3: raw landing (files + PostgreSQL) and the ingestion log table."""
import hashlib
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

from scripts.config import EXPECTED_COLUMNS, Settings

log = logging.getLogger("ingest.store")


def connect(s: Settings, attempts: int = 5, wait: float = 3.0):
    for i in range(1, attempts + 1):
        try:
            return psycopg2.connect(host=s.pg_host, port=s.pg_port, dbname=s.pg_db, user=s.pg_user, password=s.pg_password)
        except psycopg2.OperationalError as exc:
            log.warning("PostgreSQL not reachable at %s:%s (attempt %d/%d): %s", s.pg_host, s.pg_port, i, attempts, exc)
            if i == attempts:
                raise
            time.sleep(wait)


def apply_schema(conn, sql_path: str) -> None:
    """Create schemas and tables if they do not exist (the SQL file is idempotent)."""
    with conn.cursor() as cur:
        cur.execute(Path(sql_path).read_text(encoding="utf-8"))
    conn.commit()
    log.info("Schema SQL applied: %s", sql_path)


def start_run(conn, source_url: str) -> int:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO audit.ingestion_log (source_url, status) VALUES (%s, 'running') RETURNING ingestion_id",
                    (source_url,))
        run_id = cur.fetchone()[0]
    conn.commit()
    return run_id


def finish_run(conn, run_id: int, status: str, **fields) -> None:
    cols = ["status = %s", "finished_at = now()"] + ["%s = %%s" % k for k in fields]
    with conn.cursor() as cur:
        cur.execute("UPDATE audit.ingestion_log SET %s WHERE ingestion_id = %%s" % ", ".join(cols),
                    [status] + list(fields.values()) + [run_id])
    conn.commit()


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def save_landing_file(content: bytes, landing_dir: str) -> Path:
    """Keep the received bytes, untouched, as a timestamped file."""
    Path(landing_dir).mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = Path(landing_dir) / ("hour_%s.csv" % stamp)
    path.write_bytes(content)
    return path


def load_raw(conn, run_id: int, rows) -> int:
    """Full refresh of staging.stg_bike_hourly in ONE transaction: all values stay text, nothing is cleaned."""
    cols = ", ".join(EXPECTED_COLUMNS + ["ingestion_id"])
    with conn.cursor() as cur:
        cur.execute("TRUNCATE staging.stg_bike_hourly")
        execute_values(cur, "INSERT INTO staging.stg_bike_hourly (%s) VALUES %%s" % cols,
                       [tuple(r) + (run_id,) for r in rows], page_size=5000)
        cur.execute("SELECT count(*) FROM staging.stg_bike_hourly")
        loaded = cur.fetchone()[0]
    conn.commit()
    return loaded
