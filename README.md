# Python Recall

Персональная система изучения Python с интервальным повторением и необязательным
AI-наставником.

## Требования

- Python 3.12 или новее;
- [uv](https://docs.astral.sh/uv/);
- Node.js 22.13 или новее и npm;
- Docker с Docker Compose для контейнерного запуска всего приложения;
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

Compose запускает PostgreSQL 17, Backend и production Frontend. Приложение
доступно на <http://localhost:8080>; Nginx раздаёт React SPA и проксирует
`/api/v1` в Backend. Backend API также остаётся доступен напрямую на порту
`8000` для Swagger UI и разработки. Данные PostgreSQL сохраняются в
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
make release-check  Выполнить итоговую проверку Release 1 с покрытием
make release-2-check Выполнить Backend и Frontend проверки Release 2
make openapi-check  Проверить проектный OpenAPI-контракт
make migrate        Применить миграции Alembic к настроенной БД
make migration-check Проверить соответствие БД ORM-моделям
make smoke-crud     Проверить CRUD на запущенном Backend
make smoke-reviews  Проверить Review API на запущенном Backend
make smoke-frontend Проверить production Frontend и API proxy
make compose-smoke  Проверить приложение через production Frontend
make compose-config Проверить итоговую Compose-конфигурацию
make compose-up     Собрать и запустить контейнеры
make compose-down   Остановить контейнеры
make compose-logs   Смотреть логи контейнеров
```

## Frontend

Frontend находится в `frontend/` и использует отдельный npm lock-файл. При
изменении `package.json` зависимости и lock-файл обновляются командой:

```bash
make frontend-sync
```

После появления `package-lock.json` воспроизводимая установка выполняется так:

```bash
make frontend-install
```

Для локальной разработки сначала запустите Backend на порту `8000`, затем в
другом терминале запустите Vite:

```bash
make run
make frontend-run
```

Vite откроет приложение на <http://localhost:5173> и будет проксировать запросы
`/api` в Backend. Полная проверка Frontend включает актуальность OpenAPI-типов,
TypeScript, ESLint, тесты и production build:

```bash
make frontend-check
```

## Итоговая проверка Release 1

Статические проверки и тесты с минимальным покрытием 90%:

```bash
make release-check
```

Интеграционная проверка на PostgreSQL:

```bash
make compose-up
make migration-check
make smoke-crud
make smoke-reviews
```

## Итоговая проверка Release 2

Статические проверки, тесты Backend с покрытием и полный Frontend check:

```bash
make release-2-check
```

Чистая production-сборка трёх сервисов и интеграционные smoke-проверки через
Nginx proxy:

```bash
make compose-down
make compose-up
make migration-check
make compose-smoke
docker compose ps
```

После запуска пользовательский интерфейс доступен на
<http://localhost:8080>. Для финальной ручной проверки пройдите цепочку:
Category → Topic → Card → Review → Statistics.

## Документация

- [Спецификация](spec.md)
- [Архитектура](docs/architecture.md)
- [REST API](docs/api.md)
- [OpenAPI 3.1](docs/openapi.yaml)
- [План Release 2](docs/release-2-plan.md)
- [План Release 3](docs/release-3-plan.md)
- [ADR](docs/adr/)

В Release 1 реализованы Backend API, миграции, CRUD базы знаний, SM-2, Review
Engine и статистика. Release 2 добавляет React-интерфейс для управления базой
знаний, повторений и просмотра прогресса, а также production-сборку с Nginx.
AI-функции остаются необязательными и будут добавляться отдельными сценариями в
следующих релизах.
