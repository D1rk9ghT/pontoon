FROM python:3.11

WORKDIR /app

# Install system deps (important for psycopg2 etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

# Install Python deps
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Collect static files (optional but recommended)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8080

# Cloud Run uses PORT env variable
CMD gunicorn pontoon.wsgi:application --bind 0.0.0.0:$PORT
