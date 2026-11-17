"""Settings for the ingestion pipeline. Everything comes from environment variables (see .env.example)."""
import os
from dataclasses import dataclass

EXPECTED_COLUMNS = ["instant", "dteday", "season", "yr", "mnth", "hr", "holiday", "weekday", "workingday",
                    "weathersit", "temp", "atemp", "hum", "windspeed", "casual", "registered", "cnt"]
EXPECTED_ROWS = 17379  # row count of the UCI hour.csv; a different count only raises a warning

DEFAULT_SOURCE_URL = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"


def _bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "y")


@dataclass(frozen=True)
class Settings:
    source_url: str
    source_member: str          # file name inside the downloaded zip
    local_fallback_path: str    # copy of hour.csv kept in the repo
    allow_local_fallback: bool
    max_retries: int
    retry_backoff_s: float
    timeout_s: float
    landing_dir: str            # raw files are also kept here, untouched
    pg_host: str
    pg_port: int
    pg_db: str
    pg_user: str
    pg_password: str
    schema_sql: str             # DDL executed before loading (idempotent)

    @classmethod
    def from_env(cls) -> "Settings":
        e = os.environ.get
        return cls(
            source_url=e("INGEST_SOURCE_URL", DEFAULT_SOURCE_URL),
            source_member=e("INGEST_SOURCE_MEMBER", "hour.csv"),
            local_fallback_path=e("INGEST_LOCAL_FALLBACK_PATH", "data/raw/hour.csv"),
            allow_local_fallback=_bool(e("INGEST_ALLOW_LOCAL_FALLBACK", "true")),
            max_retries=int(e("INGEST_MAX_RETRIES", "3")),
            retry_backoff_s=float(e("INGEST_RETRY_BACKOFF_S", "2")),
            timeout_s=float(e("INGEST_TIMEOUT_S", "30")),
            landing_dir=e("INGEST_LANDING_DIR", "data/landing"),
            pg_host=e("POSTGRES_HOST", "localhost"),
            pg_port=int(e("POSTGRES_PORT_INTERNAL", e("POSTGRES_PORT", "5432"))),
            pg_db=e("POSTGRES_DB", "bike_sharing"),
            pg_user=e("POSTGRES_USER", "bike_user"),
            pg_password=e("POSTGRES_PASSWORD", ""),
            schema_sql=e("INGEST_SCHEMA_SQL", "sql/01_create_schemas_and_tables.sql"),
        )
