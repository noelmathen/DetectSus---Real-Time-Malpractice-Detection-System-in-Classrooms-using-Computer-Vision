FROM python:3.13-slim

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

# (Option B) Do not copy the .env file, as environment variables will be managed externally

EXPOSE 8000

# Run collectstatic at runtime so that runtime environment variables are available
CMD python manage.py collectstatic --noinput && gunicorn app.wsgi:application --bind 0.0.0.0:8000
