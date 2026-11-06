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
порту `5432`.

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

Проект пока находится на этапе инициализации. Реализован только независимый от
БД liveness endpoint. Модели, миграции и database health check будут добавлены
следующим этапом.
