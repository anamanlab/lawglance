FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend-vercel/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /tmp/requirements.txt \
    && pip install "uvicorn>=0.30.0,<1"

COPY backend-vercel/src /app/src
COPY backend-vercel/config /app/config

ENV PYTHONPATH=/app/src \
    SOURCE_POLICY_PATH=/app/config/source_policy.yaml

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "immcad_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
