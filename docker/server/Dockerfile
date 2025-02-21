FROM python:3.11-slim as base
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

FROM base as builder
RUN apt-get update && apt-get install --no-install-recommends -y build-essential curl \
    && rm -rf /var/lib/apt/lists/*
COPY server/requirements.txt ./
RUN python -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt
COPY server/ /app

FROM base as production
RUN apt-get update && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY server/ /app
RUN groupadd -r app && useradd -r -g app app \
    && chown -R app:app /app \
    && mkdir -p /logs \
    && chown -R app:app /logs
USER app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
