.DEFAULT_GOAL := help

.PHONY: help sync lock lock-check lint format format-check test check

help: ## Показать доступные команды
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "%-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

sync: ## Установить все зависимости через uv
	uv sync --all-groups

lock: ## Обновить uv.lock
	uv lock

lock-check: ## Проверить актуальность uv.lock
	uv lock --check

lint: ## Запустить Ruff linter
	uv run ruff check .

format: ## Отформатировать Python-файлы
	uv run ruff format .

format-check: ## Проверить форматирование Python-файлов
	uv run ruff format --check .

test: ## Запустить тесты
	uv run pytest

check: lock-check lint format-check test ## Выполнить все проверки

