# TradeAI

Enterprise-grade, AI-native trading operating system. Combines multi-model forecasting, RAG, and multi-agent decision-making with deterministic risk validation before paper or live execution.

## Documentation

- [System Design](docs/SYSTEM_DESIGN.md) — architectural specification (source of truth)
- [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md) — phased build plan
- [Architecture](ARCHITECTURE.md) — status and pointers

## Prerequisites

- [Docker Desktop](https://docs.docker.com/get-docker/) (Docker Engine + Compose v2)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js](https://nodejs.org/) 22+ (local frontend development only)

## Quick start (Docker — verified Phase 0)

From the repository root:

```bash
cp .env.example .env
docker compose up --build
```

Wait until all services report healthy, then verify:

```bash
curl http://localhost:8000/health
```

Expected response (HTTP 200):

```json
{"status": "ok"}
```

| Service    | URL                          |
|------------|------------------------------|
| API        | http://localhost:8000        |
| API health | http://localhost:8000/health |
| OpenAPI    | http://localhost:8000/docs   |
| Frontend   | http://localhost:3000        |
| PostgreSQL | localhost:5432               |
| Redis      | localhost:6379               |
| Qdrant     | http://localhost:6333        |

Stop the stack:

```bash
docker compose down
```

## Local development (backend only)

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

## Local development (frontend only)

Requires the API running locally or via Docker on port 8000.

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000

## Quality checks (backend)

Run from `backend/`:

```bash
uv sync
uv run ruff check app config tests
uv run ruff format --check app config tests
uv run mypy
uv run pytest
```

## Health endpoint schema

`GET /health` returns:

| Field    | Type   | Value   | Description              |
|----------|--------|---------|--------------------------|
| `status` | string | `"ok"`  | Service is up and ready. |

This schema is enforced by the `HealthResponse` Pydantic model and validated in unit tests.

## Project structure

See `docs/SYSTEM_DESIGN.md` §5 for the full directory layout.

```
TradeAI/
├── backend/app/     # FastAPI application (api, services, domain, infrastructure)
├── frontend/        # Next.js + React + Tailwind
├── docs/            # System design and roadmap
├── docker/          # Dockerfiles
└── docker-compose.yml
```

## Git branch strategy

- `main` — always deployable; protected
- `feature/<phase-name>` — e.g. `feature/market-data`, `feature/agents`
- `bugfix/<short-description>` — e.g. `bugfix/news-parser`
- `refactor/<area>` — e.g. `refactor/database`
- `docs/<topic>` — documentation-only changes

Follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`, `docs:`, `test:`.

## License

See [LICENSE](LICENSE) when added.
