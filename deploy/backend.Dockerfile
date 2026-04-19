FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend /app

RUN python -m pip install --upgrade pip \
    && if [ -f /app/requirements.txt ]; then python -m pip install -r /app/requirements.txt; \
       elif [ -f /app/pyproject.toml ]; then python -m pip install .; \
       else echo "Missing /app/requirements.txt or /app/pyproject.toml" && exit 1; fi

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
