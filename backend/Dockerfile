# ============================================================
# Nexus Alarm — backend (FastAPI + SQLite)
# Build:  docker build -t nexus-backend ./backend
# Run:    docker run -p 8000:8000 -v nexus_data:/app/data nexus-backend
# ============================================================
FROM python:3.10-slim

# Python sin buffered -> los logs de uvicorn llegan de una al contenedor
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias primero (queda en cache mientras no cambie requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código del backend
COPY . .

# /app/data es donde vive la base SQLite (se preserva con un volumen)
RUN mkdir -p /app/data

EXPOSE 8000

# Healthcheck contra /api/estado (usa urllib, no hace falta instalar curl)
HEALTHCHECK --interval=30s --timeout=6s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/estado', timeout=5).status == 200 else 1)"

# Arranque real: el entrypoint es `api:app` desde /app (== backend/)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
