FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY backend backend
COPY apps/api apps/api
COPY configs configs
COPY evaluations/cases.json evaluations/cases.json
COPY alembic.ini .
COPY migrations migrations
RUN useradd --create-home pilot && chown -R pilot:pilot /app
USER pilot
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m backend.db.seed && exec uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
