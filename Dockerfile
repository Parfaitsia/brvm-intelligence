FROM python:3.11-slim

WORKDIR /app

# Dépendances système pour playwright et psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Installe les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installe Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Copie le code
COPY app/ ./app/

# Lance l'API
CMD ["uvicorn", "app.api.routes:app", "--host", "0.0.0.0", "--port", "8080"]