# TradeAI

Enterprise-grade, AI-native trading operating system. Combines multi-model forecasting, RAG, and multi-agent decision-making with deterministic risk validation before paper or live execution.

## Documentation

- [System Design](docs/SYSTEM_DESIGN.md) — architectural specification (source of truth)
- [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md) — phased build plan
- [Architecture](ARCHITECTURE.md) — status and pointers

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js](https://nodejs.org/) 22+ (local frontend development)

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

| Service  | URL |
|----------|-----|
| API      | http://localhost:8000 |
| API health | http://localhost:8000/health |
| Frontend | http://localhost:3000 |
| PostgreSQL | localhost:5432 |
| Redis    | localhost:6379 |
| Qdrant   | http://localhost:6333 |

## Local development

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
cd backend
uv run pytest
```

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
