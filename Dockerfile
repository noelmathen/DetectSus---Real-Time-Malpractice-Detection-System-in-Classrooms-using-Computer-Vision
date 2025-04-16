FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    libffi-dev \
    libssl-dev \
    build-essential \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the entire project
COPY . .

# (Option B) Do not copy the .env file; environment variables will be provided at runtime

EXPOSE 8000

# Collect static files at runtime so that runtime environment variables are available, then start the server.
CMD python manage.py collectstatic --noinput && gunicorn app.wsgi:application --bind 0.0.0.0:8000
