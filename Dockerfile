# Tally, as one container.

FROM public.ecr.aws/docker/library/python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/tally/__init__.py src/tally/__init__.py
RUN pip install --no-cache-dir "." && pip install --no-cache-dir python-multipart

COPY src ./src
COPY web ./web
COPY rules ./rules
COPY data ./data
COPY docs ./docs
COPY evals ./evals
COPY LICENSE ./

EXPOSE 8080

CMD ["uvicorn", "tally.api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--log-level", "info"]
