FROM python:3.11-slim

WORKDIR /app

# System deps: switch default-libmysqlclient-dev → libpq-dev
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    pkg-config \
    libffi-dev \
    libssl-dev \
    build-essential \
    && apt-get clean

# Python deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# App code
COPY . .

EXPOSE 8000

CMD python manage.py migrate --noinput \
  && python manage.py collectstatic --noinput \
  && gunicorn app.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3
