FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 runner

RUN pip install --no-cache-dir pandas==2.2.3 pyarrow==16.1.0 numpy==2.0.2

USER runner
WORKDIR /work
