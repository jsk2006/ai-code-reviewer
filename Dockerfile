FROM python:3.13-slim

# Don't buffer stdout/stderr (so `docker logs` shows Django/Celery output immediately)
# and don't write .pyc files into the mounted volume.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
