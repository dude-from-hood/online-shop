# online-shop-backend

Учебный backend интернет-магазина на Python, FastAPI, PostgreSQL и Kafka (Redpanda).

## Возможности

- HTTP API для заказов и покупателей (FastAPI)
- PostgreSQL + SQL через psycopg (репозитории)
- Идемпотентность создания заказов через `Idempotency-Key`
- Бизнес-правила переходов статусов заказа (NEW → PAID → COMPLETED / CANCELLED)
- События через outbox-паттерн с публикацией в Kafka/Redpanda
- Alembic-миграции (запускаются автоматически при старте)

## Архитектура

```text
app/
├── api/
│   ├── routes/        HTTP-эндпоинты (orders, customers, health)
│   └── schemas/       Pydantic-модели запросов/ответов
├── core/              конфигурация, подключение к БД
├── repositories/      SQL-доступ к данным
└── services/          бизнес-логика, outbox-публикация
```

Поток создания заказа:

1. `POST /orders` создаёт заказ и записывает событие в таблицу `outbox_events` в той же транзакции.
2. Фоновый `OutboxPublisher` (запускается в `lifespan` приложения) каждые 2 секунды забирает PENDING-события и публикует их в Redpanda topic `orders.events`.
3. Успешно отправленные события помечаются `PROCESSED`, неудачные — `FAILED` (с повтором через 10 секунд).

### Типы событий

```json
{
  "event_id": "uuid",
  "event_type": "OrderCreated",
  "aggregate_type": "order",
  "aggregate_id": 228,
  "payload": {
    "order_id": 228,
    "customer_id": 274,
    "status": "NEW"
  }
}
```

```json
{
  "event_id": "uuid",
  "event_type": "OrderStatusChanged",
  "aggregate_type": "order",
  "aggregate_id": 228,
  "payload": {
    "order_id": 228,
    "old_status": "NEW",
    "new_status": "PAID"
  }
}
```

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

Собрать и запустить backend вместе с PostgreSQL и Redpanda:

```bash
docker compose up --build
```

После запуска доступны:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/health/db`
- `http://127.0.0.1:8000/docs`
- Redpanda Console: `http://localhost:8080` (можно смотреть события в topic `orders.events`)

Миграции Alembic выполняются автоматически перед запуском backend.

Остановить контейнеры без удаления данных:

```bash
docker compose stop
```

## Эндпоинты

### Заказы (`/orders`)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/orders` | Создать заказ (поддерживает `Idempotency-Key`) |
| GET | `/orders` | Список всех заказов |
| GET | `/orders/{order_id}` | Заказ по ID |
| GET | `/orders/search` | Поиск по `date_from`, `date_to`, `order_ids` |
| PATCH | `/orders/{order_id}/status` | Сменить статус заказа |

### Покупатели (`/customers`)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/customers` | Создать покупателя |
| GET | `/customers/{customer_id}` | Покупатель по ID |
| DELETE | `/customers/{customer_id}` | Удалить покупателя |

## Конфигурация

Основные переменные окружения (см. `.env.example`):

```env
APP_NAME=Online Shop Backend
APP_VERSION=0.1.0
APP_HOST=127.0.0.1
APP_PORT=8000
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DB=online_shop
POSTGRES_USER=online_shop
POSTGRES_PASSWORD=online_shop
KAFKA_BOOTSTRAP_SERVERS=redpanda:9092
KAFKA_ORDERS_TOPIC=orders.events
```
