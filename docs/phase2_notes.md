# Phase 2 notes: ingestion, raw storage and profiling

## 1. How the ingestion script connects to the source and handles failures

The pipeline is the Python package `scripts/` (`config.py`, `fetch.py`, `raw_store.py`, `ingest.py`), packaged in the `Dockerfile` and started by the `ingestion` service in `docker-compose.yml`.

- **Source:** The UCI zip (`INGEST_SOURCE_URL`), from which `hour.csv` is read. No cleaning is applied.
- **Retries:** The download is attempted `INGEST_MAX_RETRIES` times (default 3) with a 30-second timeout and a growing pause between attempts.
- **Structure checks (not cleaning):** The zip must contain `hour.csv`, the header must be the 17 expected columns, and every row must have 17 fields. A different row count than 17,379 only logs a warning.
- **Fallback:** If the download fails and `INGEST_ALLOW_LOCAL_FALLBACK=true`, the committed copy `data/raw/hour.csv` is used and the run is logged with `source_status = fallback_local`, so a fallback is never mistaken for a live download.
- **Failure:** Any error rolls back the load, writes `status = failed` and the error message to `audit.ingestion_log`, and exits with code 1 (the container shows as failed).
- **Networking:** The container joins `bike_net` and reaches PostgreSQL at host `postgres`, port 5432 (service name, not `localhost`). It starts only after the PostgreSQL health check passes.

## 2. Where and how raw data is stored

| Layer | Location | Content |
|---|---|---|
| Raw file | `data/landing/hour_<UTC timestamp>.csv` (host folder, not committed) | The bytes received, untouched |
| Raw table | `staging.stg_bike_hourly` | The 17 source columns, **all TEXT**, plus `ingestion_id` and `loaded_at` |
| Run log | `audit.ingestion_log` | One row per run (see below) |

Every value is stored as text so that nothing is converted before Phase 3 (for example, `dteday` stays text and `temp` stays `0.24`). Each run replaces the table contents in one transaction (`TRUNCATE` + `INSERT`), so a re-run never creates duplicates. The log keeps the SHA-256 hash of the received file, which allows checking that the stored copy is intact.

**Why raw data is kept:** It is the reference for every later step. If a cleaning rule is wrong, Phase 3 can be re-run from the untouched copy instead of downloading again, and any value in `core` can be traced back to what the source really sent.

**Execution log** (console and `audit.ingestion_log`): run start time, source status (`http_200` or `fallback_local`), rows fetched, rows loaded, file hash, final status, and error message.

## 3. Data quality issues found in the raw data (to resolve in Phase 3)

Found by profiling `hour.csv` using the local Python environment:

- **No missing values, no duplicate rows, no duplicate `instant`:** All categorical columns are inside their documented ranges, `cnt = casual + registered` on every row, and `weekday` and `workingday` agree with the date.
- **165 missing hours:** 17,379 of 17,544 possible hours are present; only 655 of 731 days have all 24 hours. The emptiest days are 2012-10-29 (1 hour) and 2011-01-27 (8 hours). The smallest `cnt` is 1, so hours are absent rather than recorded as 0. Phase 3 must decide how averages treat absent hours.
- **`windspeed = 0` in 2,180 rows (12.5%):** There are no values between 0 and 0.0896. These zeros require investigation and should not automatically be treated as calm weather without a decision.
- **`hum = 0` in 22 rows, all on 2011-03-10:** These values appear implausible and require investigation.
- **`atemp = 0` in 2 rows:** These values should be compared with `temp` before use.
- **Weather category 4 has only 3 rows:** This is too few for strong conclusions; `hours_observed` is kept in the weather mart for this reason.
- **`dteday` is text** and must become `DATE`; `temp`, `atemp`, `hum`, and `windspeed` are normalized and must be scaled back (×41, ×50, ×100, and ×67, respectively).
- **Season labels need checking:** The UCI documentation gives 1 = Spring, but season 1 starts on 2011-01-01 and codes change near March 21, June 21, September 23, and December 21. Verify the labels before reporting seasonal results.

## 4. How to run

Run these commands in Windows PowerShell from the project root:

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose logs ingestion
python -m scripts.profile_raw --csv ".\data\landing\hour_20261117T233532Z.csv"
```

The profiling command runs locally using the Python environment on the host because Pandas is not installed in the ingestion Docker image.

If the CSV filename changes after a new ingestion run, replace the filename in the profiling command with the latest file in `data/landing/`.

Check in pgAdmin (host `postgres`, port 5432):

```sql
SELECT * FROM audit.ingestion_log ORDER BY ingestion_id DESC;
SELECT count(*) FROM staging.stg_bike_hourly; -- expected 17379
```

# Pipeline-Batch-Window: 720s_RAW