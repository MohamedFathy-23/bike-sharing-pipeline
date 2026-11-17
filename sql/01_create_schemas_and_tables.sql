-- Bike Sharing Analytics Pipeline - draft DDL (Phase 1 proposal)
-- Layers: staging (raw copy) -> core (star schema) -> marts (reporting views)

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS marts;

-- Raw copy of hour.csv, loaded exactly as received (no constraints, so every source row can be loaded)
CREATE TABLE IF NOT EXISTS staging.stg_bike_hourly (
    instant     INTEGER,
    dteday      TEXT,          -- YYYY-MM-DD as in the source file, converted to DATE in core
    season      SMALLINT,
    yr          SMALLINT,
    mnth        SMALLINT,
    hr          SMALLINT,
    holiday     SMALLINT,
    weekday     SMALLINT,
    workingday  SMALLINT,
    weathersit  SMALLINT,
    temp        NUMERIC(6,4),
    atemp       NUMERIC(6,4),
    hum         NUMERIC(6,4),
    windspeed   NUMERIC(6,4),
    casual      INTEGER,
    registered  INTEGER,
    cnt         INTEGER,
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Rows that fail a validation rule
CREATE TABLE IF NOT EXISTS audit.rejected_records (
    reject_id       BIGSERIAL PRIMARY KEY,
    source_instant  INTEGER,
    failed_rule     TEXT NOT NULL,
    raw_record      JSONB,
    rejected_at     TIMESTAMPTZ NOT NULL DEFAULT now()
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
