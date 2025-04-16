FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    libffi-dev \
    libssl-dev \
    build-essential \
    && apt-get clean

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy your actual app code
COPY . .

EXPOSE 8000

CMD python manage.py collectstatic --noinput && gunicorn app.wsgi:application --bind 0.0.0.0:8000
