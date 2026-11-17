FROM python:3.12-slim

# Logs appear immediately in `docker compose logs`; no .pyc files in the image
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependencies first, so this layer is cached until requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the code and SQL are copied. Secrets come from environment variables, data from a mounted volume.
COPY scripts/ ./scripts/
COPY sql/ ./sql/

CMD ["python", "-m", "scripts.ingest"]
