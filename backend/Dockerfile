FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOMESCOUT_ENVIRONMENT=production

WORKDIR /app

RUN groupadd --system --gid 10001 homescout \
    && useradd --system --uid 10001 --gid homescout --home-dir /app homescout \
    && install -d -o homescout -g homescout /app/var/property-media /app/var/private-documents

COPY requirements.runtime.lock.txt ./requirements.runtime.lock.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check \
    -r requirements.runtime.lock.txt

COPY --chown=homescout:homescout app ./app
COPY --chown=homescout:homescout migrations ./migrations
COPY --chown=homescout:homescout alembic.ini ./alembic.ini

USER 10001:10001
EXPOSE 8000

# Migrations are a separate release operation; the server never changes schema at startup.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
