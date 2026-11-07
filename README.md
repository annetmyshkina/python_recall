# Python Recall

Персональная система изучения Python с интервальным повторением и необязательным
AI-наставником.

## Требования

- Python 3.12 или новее;
- [uv](https://docs.astral.sh/uv/);
- Docker с Docker Compose для PostgreSQL и контейнерного запуска Backend;
- GNU Make для коротких команд разработки.

## Быстрый старт Backend без Docker

```bash
cp .env.example .env
make sync
make run
```

После запуска доступны:

- liveness: <http://localhost:8000/api/v1/health>;
- готовность PostgreSQL: <http://localhost:8000/api/v1/health/database>;
- Swagger UI: <http://localhost:8000/docs>;
- ReDoc: <http://localhost:8000/redoc>.

## Запуск через Docker Compose

```bash
cp .env.example .env
make compose-up
```

Compose запускает PostgreSQL 17 и Backend. Данные PostgreSQL сохраняются в
именованном volume `python-recall_postgres_data`. PostgreSQL доступен с хоста
на `127.0.0.1:5433`, чтобы не конфликтовать с локальной БД на стандартном
порту `5432`. Перед запуском Uvicorn контейнер Backend автоматически применяет
миграции Alembic.

Для сети проекта используется подсеть `172.30.250.0/24`. Явная подсеть
позволяет Docker Compose работать при включённом VPN, который занимает все
автоматически подбираемые диапазоны. Если эта подсеть уже используется в вашей
сети, задайте свободное значение `DOCKER_SUBNET` в `.env`.

Остановка сервисов без удаления данных:

```bash
make compose-down
```

## Основные команды

```text
make sync           Установить зависимости через uv
make run            Запустить Backend с auto-reload
make test           Запустить тесты
make check          Выполнить все проверки
make openapi-check  Проверить проектный OpenAPI-контракт
make migrate        Применить миграции Alembic к настроенной БД
make migration-check Проверить соответствие БД ORM-моделям
make smoke-crud     Проверить CRUD на запущенном Backend
make smoke-reviews  Проверить Review API на запущенном Backend
make compose-config Проверить итоговую Compose-конфигурацию
make compose-up     Собрать и запустить контейнеры
make compose-down   Остановить контейнеры
make compose-logs   Смотреть логи контейнеров
```

## Документация

- [Спецификация](spec.md)
- [Архитектура](docs/architecture.md)
- [REST API](docs/api.md)
- [OpenAPI 3.1](docs/openapi.yaml)
- [ADR](docs/adr/)

В проекте реализованы core-модели Release 1, миграции Alembic, CRUD категорий,
тем, тегов и карточек, а также чистое ядро SM-2 и календарный расчёт следующего
повторения. Review API формирует очереди, сохраняет ответы отдельно и применяет
подтверждённые оценки транзакционно с защитой от повторных запросов.
