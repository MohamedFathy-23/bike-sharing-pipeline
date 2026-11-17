-- Bike Sharing Analytics Pipeline - draft DDL (Phase 1 proposal)
-- Layers: staging (raw copy) -> core (star schema) -> marts (reporting views)

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS marts;

-- Raw copy of hour.csv, loaded exactly as received (no constraints, so every source row can be loaded)
-- Raw data: preserve all source values as TEXT
CREATE TABLE IF NOT EXISTS staging.stg_bike_hourly (
    instant TEXT,
    dteday TEXT,
    season TEXT,
    yr TEXT,
    mnth TEXT,
    hr TEXT,
    holiday TEXT,
    weekday TEXT,
    workingday TEXT,
    weathersit TEXT,
    temp TEXT,
    atemp TEXT,
    hum TEXT,
    windspeed TEXT,
    casual TEXT,
    registered TEXT,
    cnt TEXT,
    ingestion_id BIGINT,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Migration for databases where the Phase 1 table already exists
ALTER TABLE staging.stg_bike_hourly
    ALTER COLUMN instant TYPE TEXT USING instant::TEXT,
    ALTER COLUMN dteday TYPE TEXT USING dteday::TEXT,
    ALTER COLUMN season TYPE TEXT USING season::TEXT,
    ALTER COLUMN yr TYPE TEXT USING yr::TEXT,
    ALTER COLUMN mnth TYPE TEXT USING mnth::TEXT,
    ALTER COLUMN hr TYPE TEXT USING hr::TEXT,
    ALTER COLUMN holiday TYPE TEXT USING holiday::TEXT,
    ALTER COLUMN weekday TYPE TEXT USING weekday::TEXT,
    ALTER COLUMN workingday TYPE TEXT USING workingday::TEXT,
    ALTER COLUMN weathersit TYPE TEXT USING weathersit::TEXT,
    ALTER COLUMN temp TYPE TEXT USING temp::TEXT,
    ALTER COLUMN atemp TYPE TEXT USING atemp::TEXT,
    ALTER COLUMN hum TYPE TEXT USING hum::TEXT,
    ALTER COLUMN windspeed TYPE TEXT USING windspeed::TEXT,
    ALTER COLUMN casual TYPE TEXT USING casual::TEXT,
    ALTER COLUMN registered TYPE TEXT USING registered::TEXT,
    ALTER COLUMN cnt TYPE TEXT USING cnt::TEXT;

ALTER TABLE staging.stg_bike_hourly
    ADD COLUMN IF NOT EXISTS ingestion_id BIGINT;

ALTER TABLE staging.stg_bike_hourly
    ADD COLUMN IF NOT EXISTS loaded_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- ==========================================
-- PHASE 2: INGESTION AUDIT LOG
-- ==========================================

CREATE TABLE IF NOT EXISTS audit.ingestion_log (
    ingestion_id BIGSERIAL PRIMARY KEY,
    source_url TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    source_status TEXT,
    rows_fetched INTEGER,
    rows_loaded INTEGER,
    file_sha256 TEXT,
    landing_file TEXT,
    error_message TEXT
);

-- ==========================================
-- PHASE 1: REJECTED RECORDS
-- ==========================================

CREATE TABLE IF NOT EXISTS audit.rejected_records (
    reject_id BIGSERIAL PRIMARY KEY,
    source_instant INTEGER,
    failed_rule TEXT NOT NULL,
    raw_record JSONB,
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- Dimensions (season attributes live in dim_date; no separate dim_season)
CREATE TABLE IF NOT EXISTS core.dim_date (
    date_key         DATE PRIMARY KEY,
    calendar_year    SMALLINT NOT NULL,
    calendar_month   SMALLINT NOT NULL CHECK (calendar_month BETWEEN 1 AND 12),
    month_name       TEXT NOT NULL,
    weekday          SMALLINT NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    weekday_name     TEXT NOT NULL,
    season_code      SMALLINT NOT NULL CHECK (season_code BETWEEN 1 AND 4),  -- 1 Spring, 2 Summer, 3 Fall, 4 Winter
    season_name      TEXT NOT NULL,
    is_holiday       BOOLEAN NOT NULL,
    is_working_day   BOOLEAN NOT NULL,
    is_weekend       BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS core.dim_weather (
    weather_key    SMALLINT PRIMARY KEY CHECK (weather_key BETWEEN 1 AND 4),
    weather_label  TEXT NOT NULL,
    description    TEXT NOT NULL
);

INSERT INTO core.dim_weather (weather_key, weather_label, description) VALUES
    (1, 'Clear',      'Clear, few clouds, partly cloudy'),
    (2, 'Mist',       'Mist and cloudy conditions'),
    (3, 'Light rain', 'Light snow or light rain with thunderstorm'),
    (4, 'Heavy rain', 'Heavy rain, ice pellets, snow and fog')
ON CONFLICT (weather_key) DO NOTHING;

-- Fact table: one row per recorded hour. hour_of_day stays here (no separate time dimension).
CREATE TABLE IF NOT EXISTS core.fact_rentals (
    rental_id      INTEGER PRIMARY KEY,                       -- instant
    date_key       DATE NOT NULL REFERENCES core.dim_date (date_key),
    hour_of_day    SMALLINT NOT NULL CHECK (hour_of_day BETWEEN 0 AND 23),
    weather_key    SMALLINT NOT NULL REFERENCES core.dim_weather (weather_key),
    temperature_c  NUMERIC(5,2),
    feels_like_c   NUMERIC(5,2),
    humidity_pct   NUMERIC(5,2),
    wind_speed     NUMERIC(5,2),
    casual         INTEGER NOT NULL CHECK (casual >= 0),
    registered     INTEGER NOT NULL CHECK (registered >= 0),
    total_rentals  INTEGER NOT NULL,
    CONSTRAINT chk_total CHECK (total_rentals = casual + registered),
    CONSTRAINT uq_date_hour UNIQUE (date_key, hour_of_day)
);
