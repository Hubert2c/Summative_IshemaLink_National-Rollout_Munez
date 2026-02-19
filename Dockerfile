# ── IshemaLink Production Dockerfile ──────────────────────────────────────────
# Base: Python 3.12 slim (minimal attack surface)
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Builder stage (compile dependencies) ──────────────────────────────────────
FROM base AS builder

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ── Production stage ──────────────────────────────────────────────────────────
FROM base AS production

COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user (security hardening)
RUN groupadd -r ishemalink && useradd -r -g ishemalink ishemalink

COPY . /app
RUN chown -R ishemalink:ishemalink /app

USER ishemalink

EXPOSE 8000

# Collect static files at build time
RUN python manage.py collectstatic --noinput || true

CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "ishemalink.asgi:application"]
