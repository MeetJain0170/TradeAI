# TradeAI Backend

FastAPI backend for the TradeAI platform. See the root `README.md` and `docs/SYSTEM_DESIGN.md` for architecture.

## Local development

```bash
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

```bash
uv run pytest
```
