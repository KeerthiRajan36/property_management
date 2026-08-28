FROM python:3.11-slim

WORKDIR /app

# System deps needed to build bcrypt/cryptography wheels if no prebuilt wheel matches
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Run migrations, then start the API. For SQLite/dev this is a no-op-safe
# sequence; for Postgres it applies the schema before serving traffic.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
