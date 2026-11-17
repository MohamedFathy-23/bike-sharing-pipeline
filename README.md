# Bike Sharing Analytics Pipeline

Data Engineering course. Phase 1: proposal and environment setup. Phase 2: containerized ingestion and raw storage.

An end-to-end pipeline for the UCI Bike Sharing dataset (`hour.csv`, 17,379 hourly rows, 2011 to 2012):

```
hour.csv (UCI) -> Python Ingestion -> PostgreSQL (staging -> core -> marts) -> Metabase Dashboard
```

Kestra is the orchestration layer across this pipeline (scheduling, triggering, monitoring and managing runs).
Docker Compose runs PostgreSQL 16, pgAdmin 4 and (from Phase 2) the ingestion container; Kestra and Metabase come in later phases.

## Analytical questions

1. How does hourly demand differ between working days, weekends and holidays, and when does it peak?
2. How do weather and temperature affect rentals, for casual versus registered users?
3. How did monthly demand and the user mix change from 2011 to 2012, and what is the seasonal pattern?

Full details: [`docs/Phase1_Proposal.pdf`](docs/Phase1_Proposal.pdf).

## Prerequisites

- Docker Desktop (or Docker Engine) with the Compose plugin
- Git

## Run the environment

```bash
git clone <repo-url>
cd bike-sharing-pipeline

cp .env.example .env        # then edit the passwords in .env
docker compose up -d
docker compose ps           # postgres should show "healthy"
```

| Service  | URL / address              | Notes                                   |
|----------|----------------------------|-----------------------------------------|
| pgAdmin  | http://localhost:5050      | Login with `PGADMIN_DEFAULT_EMAIL` and `PGADMIN_DEFAULT_PASSWORD` from `.env` |
| PostgreSQL | `localhost:5432`         | Database, user and password from `.env` |

### Connect pgAdmin to PostgreSQL

1. Open http://localhost:5050 and log in.
2. Right-click **Servers**, then **Register > Server**.
3. **General** tab: Name = `bike-postgres`.
4. **Connection** tab:
   - Host name/address: `postgres`
   - Port: `5432`
   - Maintenance database: value of `POSTGRES_DB`
   - Username / Password: values of `POSTGRES_USER` / `POSTGRES_PASSWORD`

### How the containers talk to each other

Both services are on the Docker network `bike_net`. Inside that network a container reaches another one by its
**service name**, so pgAdmin uses host `postgres` (not `localhost`, which would point to the pgAdmin container itself).
From your laptop, use `localhost` and the published ports.

### Data persistence

Data lives in the named volumes `postgres_data` and `pgadmin_data`.

```bash
docker compose down        # stops containers, data is kept
docker compose up -d       # data is still there
docker compose down -v     # WARNING: also deletes the volumes
```

### Optional: create the draft schema

```bash
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < sql/01_create_schemas_and_tables.sql
```

(On Windows PowerShell, open pgAdmin's Query Tool and run the file instead.)

## Phase 2: ingestion and raw storage

```bash
docker compose up -d --build      # starts postgres, pgadmin, then runs the ingestion container once
docker compose logs ingestion     # source status, records fetched, SUCCESS line
docker compose run --rm ingestion # run the ingestion again
docker compose run --rm ingestion python -m scripts.profile_raw   # raw data profile
```

Raw data lands in `staging.stg_bike_hourly` (all columns TEXT, untouched) and in `data/landing/` (not committed).
Each run is recorded in `audit.ingestion_log`. Details and the list of data quality issues: [`docs/phase2_notes.md`](docs/phase2_notes.md).

If you created `staging.stg_bike_hourly` in Phase 1, drop it once (`DROP TABLE staging.stg_bike_hourly;`) so it is recreated
with the raw TEXT columns.

## Repository structure

```
docs/               proposal, architecture diagram, data dictionary
scripts/            Python extraction, validation, transformation and loading
sql/                schema creation, tables, quality checks, marts views
flows/              Kestra YAML orchestration flows
data/raw/hour.csv   source dataset
docker-compose.yml  PostgreSQL 16, pgAdmin 4 and the ingestion service
Dockerfile          ingestion image
.env.example        environment variables without secrets
requirements.txt    Python dependencies
```
## Team

| Name | ID | Role |
|------|----|------|
| [Mohamed Ahmed Fathy Ahmed] | [ID]  |
| [Osman Osama Osman ] | [ID]  |


## Roadmap

- [x] Phase 1: proposal, architecture, Docker + PostgreSQL + pgAdmin
- [x] Phase 2: containerized ingestion, raw storage, execution log, raw profiling
