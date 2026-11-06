FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# libgomp1 est requis par XGBoost et Scikit-Learn sur Linux Debian-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Exécution sous un utilisateur non-root
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app/ ./app/

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD sh -c 'curl -f http://127.0.0.1:${PORT:-8000}/health || exit 1'

# Utilise la variable dynamique PORT injectée par Render (fallback sur 8000 en local)
CMD ["sh", "-c", "uvicorn app.Fast_api_price:app --host 0.0.0.0 --port ${PORT:-8000}"]
