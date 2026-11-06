FROM ghcr.io/astral-sh/uv:0.12.15 AS uv

FROM python:3.12-slim

COPY --from=uv /uv /uvx /bin/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend ./backend

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
