# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml README.md ./
RUN pip install --upgrade pip && pip install --no-cache-dir build
COPY . ./
RUN python -m build --wheel --outdir /tmp/wheels

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY --from=builder /tmp/wheels /tmp/wheels
RUN pip install --upgrade pip && pip install /tmp/wheels/*.whl
COPY . ./
CMD ["python", "main.py"]
