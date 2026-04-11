FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements /tmp/requirements
RUN pip install --no-cache-dir -r /tmp/requirements/dev.txt

COPY backend /app/backend
COPY docker /app/docker

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
