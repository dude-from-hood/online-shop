# online-shop-backend

Учебный backend интернет-магазина на Python, FastAPI и PostgreSQL.

## Первый запуск

Требования: Python 3.12+ и [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run uvicorn app.main:app --reload
```

После запуска доступны:

- `GET http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`

Конфигурация задаётся переменными окружения. Для локальной разработки можно скопировать `.env.example` в `.env`.

## Запуск через Docker Compose

Собрать и запустить backend вместе с PostgreSQL:

```bash
docker compose up --build
```

После запуска доступны:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/health/db`
- `http://127.0.0.1:8000/docs`

Миграции Alembic выполняются автоматически перед запуском backend.

Остановить контейнеры без удаления данных:

```bash
docker compose stop
```
