.DEFAULT_GOAL := help

.PHONY: help sync lock lock-check run lint format format-check openapi-check migration-sql-check migrate migration-check test test-cov check smoke-crud compose-config compose-up compose-down compose-logs

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
	uv run python scripts/validate_openapi.py

migration-sql-check: ## Проверить генерацию SQL всех миграций без подключения к БД
	uv run alembic upgrade head --sql > /dev/null

migrate: ## Применить миграции к настроенной БД
	uv run alembic upgrade head

migration-check: ## Проверить, что схема БД соответствует ORM-моделям
	uv run alembic check

test: ## Запустить тесты
	uv run pytest

test-cov: ## Запустить тесты с отчётом покрытия Backend
	uv run pytest --cov=backend/app --cov-report=term-missing

check: lock-check lint format-check openapi-check migration-sql-check test ## Выполнить все проверки

smoke-crud: ## Проверить CRUD на запущенном Backend и удалить тестовые данные
	uv run python scripts/smoke_crud.py

compose-config: ## Проверить Docker Compose конфигурацию
	docker compose config --quiet

compose-up: ## Собрать и запустить Backend и PostgreSQL
	docker compose up --build --detach --wait --wait-timeout 60

compose-down: ## Остановить контейнеры без удаления данных
	docker compose down

compose-logs: ## Смотреть логи контейнеров
	docker compose logs --follow
