"""Containerized ingestion: source -> untouched raw copy (file + PostgreSQL) -> execution log.
Run:  python -m scripts.ingest        (inside the container this is the default command)"""
import logging
import sys
from datetime import datetime, timezone

from scripts import fetch, raw_store
from scripts.config import Settings

LOG_FORMAT = "%(asctime)s | INGEST-AUDIT-ECU26 | %(levelname)-7s | %(name)s | %(message)s"
log = logging.getLogger("ingest")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stdout)
    s = Settings.from_env()
    started = datetime.now(timezone.utc)
    log.info("Ingestion started at %s", started.isoformat())

    conn = raw_store.connect(s)
    raw_store.apply_schema(conn, s.schema_sql)
    run_id = raw_store.start_run(conn, s.source_url)
    try:
        result = fetch.fetch_source(s)
        log.info("Source status: %s (origin: %s, %d bytes)", result.source_status, result.origin, len(result.content))

        header, rows = fetch.parse_csv(result.content)
        fetch.check_structure(header, rows)
        log.info("Records fetched: %d rows, %d columns", len(rows), len(header))

        landing = raw_store.save_landing_file(result.content, s.landing_dir)
        digest = raw_store.sha256(result.content)
        log.info("Raw file kept at %s (sha256 %s)", landing, digest)

        loaded = raw_store.load_raw(conn, run_id, rows)
        raw_store.finish_run(conn, run_id, "success", source_status=result.source_status, rows_fetched=len(rows),
                             rows_loaded=loaded, file_sha256=digest, landing_file=str(landing))
        log.info("Ingestion SUCCESS: run_id=%d, rows_fetched=%d, rows_loaded=%d into staging.stg_bike_hourly",
                 run_id, len(rows), loaded)
        return 0
    except Exception as exc:  # log the failure in the database, then fail the container
        conn.rollback()
        log.exception("Ingestion FAILED: %s", exc)
        raw_store.finish_run(conn, run_id, "failed", error_message=str(exc)[:1000])
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
