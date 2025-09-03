FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*


RUN pip install --no-cache-dir poetry==2.1.1


RUN poetry config virtualenvs.create false \
    && poetry config installer.max-workers 10 \
    && poetry config installer.no-binary false

COPY pyproject.toml poetry.lock* /app/

RUN poetry install --no-interaction --no-ansi --no-root --timeout=600 || \
    (echo "First attempt failed, trying with pip fallback..." && \
     poetry export -f requirements.txt --output requirements.txt && \
     pip install -r requirements.txt)


COPY ./src /app/src/

RUN poetry install --no-interaction --no-ansi --timeout=300 || \
    pip install -e .

CMD ["python", "-m", "notifier"]