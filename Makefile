.DEFAULT_GOAL := help

.PHONY: help sync lock lock-check run lint format format-check openapi-check migration-sql-check migrate migration-check test test-cov check release-check release-2-check release-3-check frontend-sync frontend-install frontend-run frontend-api-generate frontend-check smoke-crud smoke-reviews smoke-ai-fake smoke-ai-live smoke-frontend compose-smoke compose-config compose-up compose-down compose-logs

help: ## Показать доступные команды
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "%-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

sync: ## Установить все зависимости через uv
	uv sync --all-groups

lock: ## Обновить uv.lock
	uv lock

lock-check: ## Проверить актуальность uv.lock
	uv lock --check

run: ## Запустить Backend в режиме разработки
	uv run uvicorn backend.app.main:app --reload

lint: ## Запустить Ruff linter
	uv run ruff check .

format: ## Отформатировать Python-файлы
	uv run ruff format .

format-check: ## Проверить форматирование Python-файлов
	uv run ruff format --check .

openapi-check: ## Проверить OpenAPI-контракт
	uv run python -m scripts.validate_openapi

migration-sql-check: ## Проверить генерацию SQL всех миграций без подключения к БД
	uv run alembic upgrade head --sql > /dev/null

migrate: ## Применить миграции к настроенной БД
	uv run alembic upgrade head

migration-check: ## Проверить, что схема БД соответствует ORM-моделям
	uv run alembic check

test: ## Запустить тесты
	uv run pytest

test-cov: ## Запустить тесты с отчётом покрытия Backend
	uv run pytest --cov=backend/app --cov-report=term-missing --cov-fail-under=90

check: lock-check lint format-check openapi-check migration-sql-check test ## Выполнить все проверки

release-check: lock-check lint format-check openapi-check migration-sql-check compose-config test-cov ## Проверить готовность Release 1

release-2-check: release-check frontend-check ## Выполнить все статические проверки и тесты Release 2

release-3-check: release-2-check smoke-ai-fake ## Выполнить автоматические проверки Release 3 без внешнего Ollama

frontend-sync: ## Установить или обновить зависимости Frontend и lock-файл
	npm --prefix frontend install

frontend-install: ## Установить зависимости Frontend из lock-файла
	npm --prefix frontend ci

frontend-run: ## Запустить Frontend в режиме разработки
	npm --prefix frontend run dev

frontend-api-generate: ## Обновить TypeScript-типы из OpenAPI
	npm --prefix frontend run api:generate

frontend-check: ## Выполнить все проверки Frontend
	npm --prefix frontend run check

smoke-crud: ## Проверить CRUD на запущенном Backend и удалить тестовые данные
	uv run python scripts/smoke_crud.py

smoke-reviews: ## Проверить Review API на запущенном Backend и удалить тестовые данные
	uv run python -m scripts.smoke_reviews

smoke-ai-fake: ## Проверить все AI-сценарии с детерминированным fake-провайдером
	uv run python -m scripts.smoke_ai_fake

smoke-ai-live: ## Проверить все AI-сценарии с настоящим Ollama (opt-in)
	@test "$${RUN_LIVE_AI_SMOKE:-0}" = "1" || (echo "Добавьте RUN_LIVE_AI_SMOKE=1 для запуска настоящей модели."; exit 2)
	uv run python -m scripts.smoke_ai_live

smoke-frontend: ## Проверить production Frontend, SPA-маршруты и API proxy
	uv run python -m scripts.smoke_frontend

compose-smoke: ## Проверить всё приложение через production Frontend
	FRONTEND_URL="$${FRONTEND_URL:-http://localhost:8080}" uv run python -m scripts.smoke_frontend
	SMOKE_API_BASE_URL="$${FRONTEND_URL:-http://localhost:8080}/api/v1" uv run python scripts/smoke_crud.py
	SMOKE_API_BASE_URL="$${FRONTEND_URL:-http://localhost:8080}/api/v1" uv run python -m scripts.smoke_reviews

compose-config: ## Проверить Docker Compose конфигурацию
	docker compose config --quiet

compose-up: ## Собрать и запустить Frontend, Backend и PostgreSQL
	docker compose up --build --detach --wait --wait-timeout 60

compose-down: ## Остановить контейнеры без удаления данных
	docker compose down

compose-logs: ## Смотреть логи контейнеров
	docker compose logs --follow
