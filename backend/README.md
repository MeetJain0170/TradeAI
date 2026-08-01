# TradeAI Backend

FastAPI backend for the TradeAI platform. See the root `README.md` and `docs/SYSTEM_DESIGN.md` for architecture.

## Local development

```bash
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Quality checks

```bash
uv run ruff check app config tests
uv run ruff format --check app config tests
uv run mypy
uv run pytest
```

## Tests

```bash
uv run pytest
```

Tests use `httpx2` (not `httpx`) as required by Starlette's `TestClient`.
