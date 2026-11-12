# Python Recall

Персональная система изучения Python с интервальным повторением и необязательным
AI-наставником.

## Требования

- Python 3.12 или новее;
- [uv](https://docs.astral.sh/uv/);
- Node.js 22.13 или новее и npm 9.5 или новее;
- Docker с Docker Compose для контейнерного запуска всего приложения;
- GNU Make для коротких команд разработки.

Для необязательных AI-сценариев также нужны
[Ollama](https://ollama.com/) и локальная модель `qwen3:4b`.

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

## Локальный ИИ через Ollama

Основная часть приложения не зависит от ИИ. При `AI_ENABLED=false` карточки,
повторения и статистика продолжают работать, а интерфейс объясняет, что анализ
отключён. Чтобы включить сценарии Release 3, установите модель и задайте
настройки в `.env`:

```bash
ollama pull qwen3:4b
```

```dotenv
AI_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
COMPOSE_OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3:4b
```

`OLLAMA_BASE_URL` используется Backend при запуске на хосте, а
`COMPOSE_OLLAMA_BASE_URL` — контейнером. На Linux Ollama должна принимать
соединения от Docker bridge. Для systemd можно создать
`/etc/systemd/system/ollama.service.d/docker.conf`:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

Затем примените настройку:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
make compose-up
curl http://localhost:8000/api/v1/ai/providers
```

`0.0.0.0` открывает порт Ollama на сетевых интерфейсах компьютера. Не
публикуйте `11434` в недоверенную сеть: ограничьте доступ локальным firewall
или привяжите сервис только к адресу, доступному Docker.

## Основные команды

```text
make sync           Установить зависимости через uv
make run            Запустить Backend с auto-reload
make test           Запустить тесты
make check          Выполнить все проверки
make release-check  Выполнить итоговую проверку Release 1 с покрытием
make release-2-check Выполнить Backend и Frontend проверки Release 2
make release-3-check Выполнить проверки Release 3 с fake AI-провайдером
make openapi-check  Проверить проектный OpenAPI-контракт
make migrate        Применить миграции Alembic к настроенной БД
make migration-check Проверить соответствие БД ORM-моделям
make smoke-crud     Проверить CRUD на запущенном Backend
make smoke-reviews  Проверить Review API на запущенном Backend
make smoke-ai-fake  Проверить AI-сценарии без внешней модели
make smoke-ai-live  Проверить AI-сценарии с настоящим Ollama (opt-in)
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

## Итоговая проверка Release 3

Полный автоматический набор без зависимости от Ollama включает Backend,
Frontend и детерминированный smoke-тест всех AI-сценариев:

```bash
make release-3-check
```

После запуска Compose проверьте PostgreSQL, production proxy и настоящую
модель. Live smoke создаёт временные данные, проверяет Answer Evaluator, Card
Analyzer, Card Generator, идемпотентность и отсутствие автоматического
изменения SM-2, а затем удаляет свои данные:

```bash
make compose-up
make migration-check
make compose-smoke
RUN_LIVE_AI_SMOKE=1 make smoke-ai-live
docker compose ps
```

Ручная проверка интерфейса на <http://localhost:8080>:

1. В повторении сохранить собственный ответ, отдельно запросить ИИ-анализ,
   при необходимости исправить ответ, затем самостоятельно выбрать оценку.
2. В форме карточки запустить анализ качества и убедиться, что предложения ИИ
   не применяются без действия пользователя.
3. На странице «ИИ-наставник» сгенерировать черновики, принять один и отклонить
   другой; карточка должна появиться только после принятия.
4. Убедиться, что счётчики использования обновились и пользовательские тексты
   не отображаются в технической статистике.

Отказоустойчивость проверяется отдельно: при `AI_ENABLED=false` статус
провайдера должен быть `disabled`; при остановленной Ollama основной health и
CRUD остаются рабочими, а `/health/ai` возвращает `503`:

```bash
sudo systemctl stop ollama
curl http://localhost:8000/api/v1/health
curl -i http://localhost:8000/api/v1/health/ai
make smoke-crud
sudo systemctl start ollama
```

## Документация

- [Спецификация](spec.md)
- [Архитектура](docs/architecture.md)
- [REST API](docs/api.md)
- [OpenAPI 3.1](docs/openapi.yaml)
- [План Release 2](docs/release-2-plan.md)
- [План Release 3](docs/release-3-plan.md)
- [План Release 4](docs/release-4-plan.md)
- [ADR](docs/adr/)

В Release 1 реализованы Backend API, миграции, CRUD базы знаний, SM-2, Review
Engine и статистика. Release 2 добавляет React-интерфейс и production-сборку с
Nginx. Release 3 добавляет необязательный локальный ИИ: анализ ответа, анализ
качества карточки, генерацию черновиков с явным принятием и страницу
ИИ-наставника. Только пользовательская оценка меняет состояние SM-2; ИИ не
применяет изменения к учебным данным автоматически.
