# TradeAI Implementation Roadmap

## Project Overview

TradeAI is an enterprise-grade, AI-native trading operating system that combines multi-model forecasting, Retrieval-Augmented Generation (RAG), and a multi-agent (LangGraph) decision system to produce transparent, evidence-backed trading recommendations, validated by a deterministic Risk Engine before any paper or live execution through broker adapters (Upstox, Zerodha).

This roadmap converts `SYSTEM_DESIGN.md` — treated as the immutable, final architectural specification — into an incremental, dependency-respecting build plan for a **solo developer**. It does not alter, simplify, or reinterpret the architecture. Every subsystem named in the design document (Market Data, Feature Engineering, Forecasting, Ensemble, RAG, Multi-Agent, Decision Engine, Risk Engine, Portfolio Engine, Trade Logger, Broker Layer, Notification Service, RLAIF, Database, API, Frontend, Botpress, Testing, Deployment) is mapped to exactly one phase where it is *introduced*, and to later phases where it is *extended*.

Each phase is scoped so that, at the end of it, `docker compose up` (or the local dev equivalent) produces a running, testable application — never a partially-wired system that only compiles.

## Development Principles

- **Clean Architecture**: presentation → API → business services → infrastructure. Dependencies point inward; infrastructure never leaks into business logic.
- **SOLID & Dependency Injection**: every external dependency (LLM, broker, model, vector store) sits behind an interface (`Base`* / `*Interface`) injected via FastAPI's dependency system.
- **Interface-first sequencing**: whenever a phase introduces a family of interchangeable implementations (forecast models, brokers, LLM providers), the abstract interface is built and tested *before* the first concrete implementation, so the second and third implementations are drop-in.
- **No circular dependencies**: a phase may only depend on services/tables delivered in strictly earlier phases. Where the source document's suggested ordering would create a cycle (e.g., Portfolio Engine "synchronizes with the Broker Layer" while also being listed before it), this roadmap builds the *data model and paper-trading path* first and defers *live broker synchronization* to the Broker Layer phase — see the ordering note in Phase 12.
- **Always shippable**: every phase ends in a working app state with passing tests — no phase leaves the repo in a broken or half-migrated state.
- **No duplicate work**: shared concerns (schemas, DI wiring, logging, error handling) are built once, in Phase 0–1, and reused everywhere.
- **Production-readiness from day one**: type hints, Pydantic validation, structured logging, and tests are not deferred to a "cleanup phase" — they are part of every phase's Definition of Done.

---



## Phase 0 – Project Foundation

**Goal:** Establish the empty-repo skeleton exactly matching the folder structure in `SYSTEM_DESIGN.md` §5, with a running (but empty) FastAPI app and Next.js app wired through Docker Compose.

**Why this phase comes now:** Nothing can be built without a repo skeleton, dependency manager, and a way to run the stack locally. This is the only phase with no functional dependencies.

**Dependencies:** None.

**Deliverables:**

- Full directory tree from §5 created (`backend/app/{api,domain,services,infrastructure}`, `backend/config`, `backend/tests/{unit,integration,e2e}`, `backend/external`, `frontend/{app,components,lib,public}`, `docs/`, `docker/`).
- `uv`-managed Python project (`pyproject.toml`, `uv.lock`) for the backend.
- Next.js + TypeScript + Tailwind CSS scaffold for the frontend.
- `docker-compose.yml` defining empty/stub services: `api`, `frontend`, `postgres`, `redis`, `qdrant`.
- `README.md`, `ARCHITECTURE.md` stub, `.gitignore`, `.env.example` (no real secrets).
- `main.py` with a FastAPI app exposing only `/health`.
- Git initialized with `main` branch and branch-naming convention documented (see Final Section).

**Folder(s) affected:** entire repo (initial creation).

**Services implemented:** none (infrastructure only).

**APIs introduced:** `GET /health`.

**Database tables introduced:** none.

**External integrations:** none.

**Testing requirements:** one smoke test (`test_health.py`) asserting `/health` returns `200`. CI workflow stub (GitHub Actions) that runs `uv run pytest`.

**Completion checklist:**

- [x] `docker compose up` starts api, frontend, postgres, redis, qdrant containers without error.
- [x] `GET /health` returns 200 from both host and container.
- [x] `uv run pytest` passes with 1 test.
- [x] Repo pushed with `main` branch and initial commit following conventional commits.

**Estimated complexity:** Low.
**Estimated implementation effort:** 0.5–1 day.

---



## Phase 1 – Configuration & Logging Infrastructure

**Goal:** Centralize all environment/config loading and structured logging so every later phase has a single, consistent way to read settings and emit logs.

**Why this phase comes now:** Per the dependency chain (Configuration → Logging → Database → …), every subsequent service needs `Settings` and a logger. Building this first prevents duplicated ad-hoc `os.getenv` calls and inconsistent logging formats later.

**Dependencies:** Phase 0.

**Deliverables:**

- `backend/config/settings.py`: Pydantic `Settings` class reading all environment variables named in §20/§24 (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `VECTOR_DB_URL`, broker/LLM keys as optional placeholders), cached via `lru_cache`/DI.
- `backend/app/infrastructure/logging/`: structured JSON logging setup (Python `logging` + custom formatter), request-id middleware.
- Global exception-handling middleware in `main.py` producing the standardized error response shape from §21.
- Base custom exception hierarchy (`TradeAIError`, `*Error`/`*Exception` suffix convention from §8).

**Folder(s) affected:** `backend/config/`, `backend/app/infrastructure/logging/`, `backend/app/main.py`.

**Services implemented:** none (cross-cutting infrastructure only).

**APIs introduced:** none (middleware only, applied globally).

**Database tables introduced:** none.

**External integrations:** none.

**Testing requirements:** unit tests for `Settings` loading/validation and for the error-handler middleware producing the correct JSON error envelope; unit test that a raised custom exception is logged without leaking secrets.

**Completion checklist:**

- [ ] All env vars from `.env.example` load into a validated `Settings` object; missing required vars fail fast at startup.
- [ ] Every request produces a structured log line with request ID, method, path, status, duration.
- [ ] Uncaught exceptions return the standardized error JSON (never a raw stack trace) and are logged server-side.
- [ ] No secrets ever appear in logs (verified by test).

**Estimated complexity:** Low.
**Estimated implementation effort:** 1 day.

---



## Phase 2 – Database Foundation & Repository Layer

**Goal:** Stand up PostgreSQL with SQLAlchemy + Alembic, and implement the repository pattern for the first, foundational tables: `users`, `audit_logs`, `system_logs`.

**Why this phase comes now:** Per the dependency chain (Database → Repositories), nearly everything downstream persists data. Building the ORM/session/migration machinery once, plus the repository abstraction, avoids re-deriving this pattern per-feature.

**Dependencies:** Phase 1.

**Deliverables:**

- SQLAlchemy async engine/session factory under `backend/app/infrastructure/database/`.
- Alembic configured with autogenerate; first migration creating `users`, `audit_logs`, `system_logs`.
- Generic `BaseRepository[T]` abstract class (CRUD + pagination) plus `UserRepository`.
- `domain/models/` SQLAlchemy models and `domain/schemas/` Pydantic schemas for `User` (matching naming conventions in §8: `UserLoginRequest`, etc., introduced here for reuse in Phase 3).
- Soft-delete convention (`deleted_at`) established for critical entities, per §20.

**Folder(s) affected:** `backend/app/infrastructure/database/`, `backend/app/domain/models/`, `backend/app/domain/schemas/`, `backend/app/services/` (repository interfaces only).

**Services implemented:** `UserRepository` (data-access only — no business/auth service yet).

**APIs introduced:** none.

**Database tables introduced:** `users`, `audit_logs`, `system_logs`.

**External integrations:** PostgreSQL.

**Testing requirements:** integration tests against a disposable test database (docker-based) for CRUD + soft delete + pagination on `UserRepository`; migration up/down test.

**Completion checklist:**

- [ ] `alembic upgrade head` / `alembic downgrade base` both succeed cleanly.
- [ ] `UserRepository` CRUD operations covered by integration tests, isolated from prod DB.
- [ ] Foreign keys, unique constraints, and indexes applied per §20 conventions.
- [ ] No raw SQL used outside justified performance cases (per §7).

**Estimated complexity:** Medium.
**Estimated implementation effort:** 1.5–2 days.

---



## Phase 3 – Authentication, Authorization & Core API Skeleton

**Goal:** Implement a production-ready authentication and authorization layer using JWT, establish the versioned API structure (`/api/v1/...`), configure Redis-backed rate limiting and refresh-token management, and provide the security foundation for every future endpoint.

**Why this phase comes now:** Every future API—including Market Data, Forecasting, RAG, Agents, Trading, Portfolio, and Broker integrations—requires authenticated users, consistent authorization, request validation, and standardized routing. Implementing authentication first prevents retrofitting security across dozens of endpoints later.

**Dependencies:** Phase 2 (`users` table).

---

## Deliverables

### Authentication Layer

Implement under:

```text
backend/app/security/
```

### PasswordService

Responsible only for password operations.

Functions:

- `hash_password()`
- `verify_password()`
- `validate_password_strength()`

Password policy:

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

---

### JWTService

Responsible only for JWT creation and validation.

Functions:

- `create_access_token()`
- `create_refresh_token()`
- `decode_token()`
- `verify_token()`

JWT payload must contain:

- `sub`
- `email`
- `role`
- `iat`
- `exp`
- `jti`
- `token_type`

Both Access and Refresh Tokens must contain unique `jti` values.

---

### AuthService

Responsible for authentication business logic.

Functions:

- `register()`
- `login()`
- `logout()`
- `refresh()`

AuthService coordinates:

- PasswordService
- JWTService
- UserRepository
- Redis

---

## Authorization (RBAC)

Implement under:

```text
backend/app/security/
```

Create:

- `roles.py`
- `permissions.py`

Implement:

- `Role` enum
- `Permission` enum
- `RoleChecker` dependency

Do **not** implement decorator-based RBAC yet.

The design should support future roles such as:

- Admin
- Trader
- Researcher
- ReadOnly

---

## Redis Infrastructure

Implement under:

```text
backend/app/infrastructure/redis/
```

Redis will be used for:

- Refresh Token tracking
- Refresh Token revocation
- Rate limiting
- Temporary authentication cache

Do **not** implement server-side sessions.

JWT authentication should remain stateless.

Only Refresh Token JTIs should be stored.

---

## API Skeleton

Establish the permanent API structure.

```text
/api/v1/

├── auth/
├── users/
├── health/
└── system/
```

Only `auth` will contain endpoints during this phase.

The remaining folders are created now to stabilize the API structure for future phases.

---

## Authentication Endpoints

Implement:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/profile`

### Registration Requirements

- Email normalization (convert to lowercase)
- Password confirmation
- Duplicate email validation
- Password strength validation

### Login

- Authenticate using email only
- Verify password
- Return Access Token and Refresh Token

### Logout

- Revoke Refresh Token JTI in Redis

### Profile

- Protected endpoint using JWT authentication

---

## FastAPI Dependencies

Update:

```text
backend/app/api/dependencies.py
```

Provide:

- `get_current_user()`
- `get_current_active_user()`
- `RoleChecker()`
- `RateLimiter()`

Services should never decode JWTs manually.

Authentication must always go through dependency injection.

---

## Rate Limiting

Implement Redis-backed configurable rate limiting.

Example:

```python
RateLimiter(limit=100, window=60)
```

Future endpoint-specific limits should be configurable, for example:

| Endpoint | Limit |
|----------|------:|
| Login | 5 requests/minute |
| Chat | 20 requests/minute |
| Forecast | 60 requests/minute |

Do not hardcode rate limits.

---

## Response Envelope

From this phase onward every endpoint must return the standardized API response format.

### Success

```json
{
  "success": true,
  "data": {}
}
```

### Failure

```json
{
  "success": false,
  "error": {}
}
```

No endpoint should return raw dictionaries.

---

## OpenAPI Documentation

Configure Swagger UI with:

- JWT Bearer Authentication
- Request examples
- Response examples
- Endpoint descriptions
- Tags
- HTTP status documentation

Protected endpoints should automatically display authentication requirements.

---

## Folder(s) Affected

```text
backend/app/api/v1/auth/

backend/app/api/dependencies.py

backend/app/services/auth/

backend/app/security/

backend/app/infrastructure/redis/
```

---

## Services Implemented

- PasswordService
- JWTService
- AuthService

---

## APIs Introduced

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/profile`

---

## Database

No new primary business tables.

Redis stores:

- Refresh Token JTIs
- Rate limiting counters

If persistent refresh-token metadata is preferred over Redis-only storage, introduce:

- `refresh_tokens`

Otherwise Redis alone is sufficient.

---

## External Integrations

- PostgreSQL
- Redis

---

## Testing Requirements

### Unit Tests

**PasswordService**

- Password hashing
- Password verification
- Weak password rejection

**JWTService**

- Access Token creation
- Refresh Token creation
- Expired Token rejection
- Invalid Token rejection
- Malformed JWT rejection

**AuthService**

- Registration
- Login
- Logout
- Refresh

---

### API Tests

#### Register

- Successful registration
- Duplicate email
- Weak password
- Password confirmation mismatch

#### Login

- Successful login
- Invalid credentials

#### Refresh

- Successful refresh
- Expired Refresh Token
- Revoked Refresh Token

#### Profile

- Successful access
- Missing Authorization header
- Invalid Bearer format
- Invalid JWT
- Expired JWT

#### Rate Limiting

- Verify repeated requests are throttled

#### RBAC

- Verify unauthorized roles are denied access

---

## Completion Checklist

- [ ] User registration works successfully.
- [ ] Email normalization implemented.
- [ ] Password policy enforced.
- [ ] Password confirmation enforced.
- [ ] Login returns Access Token and Refresh Token.
- [ ] Protected endpoints authenticate correctly.
- [ ] Logout revokes Refresh Token JTI.
- [ ] Expired and malformed JWTs are rejected.
- [ ] Redis-backed rate limiting verified.
- [ ] Swagger UI documents authentication correctly.
- [ ] Standard response envelope applied to every endpoint.
- [ ] Unit tests pass.
- [ ] API tests pass.
- [ ] Ruff passes.
- [ ] MyPy passes.
- [ ] Pytest passes.

---

## Estimated Complexity

**Medium–High**

---

## Estimated Implementation Effort

**2–3 days**

# Phase 4 – Market Data Layer

## Goal

Implement `BaseMarketDataProvider` and a first concrete provider (**Yahoo Finance**, as the lowest-friction data source), along with the `stocks` and `market_data` database tables and the Market Data API.

## Why This Phase Comes Now

Per the dependency chain, **Market Data** is the first "content" layer of the system. Every downstream component—feature engineering, forecasting, AI agents, risk analysis, portfolio management, and execution—depends on clean and reliable market data.

Broker-based providers (Upstox, Zerodha, etc.) are intentionally deferred until **Phase 14 (Broker Layer)** because they require authenticated broker integrations.

## Dependencies

- ✅ Phase 2 – Database Foundation & Repository Layer
- ✅ Phase 3 – Authentication & Core API Skeleton

---

# Deliverables

### Market Data Providers

Implement a provider abstraction under:

```text
backend/app/services/market_data/
```

Components:

- `BaseMarketDataProvider`
  - `initialize()`
  - `get_quote()`
  - `get_history()`
  - `get_indices()`
  - `get_options_chain()`
  - `health_check()`
  - `shutdown()`
- `YahooFinanceProvider`
  - First concrete implementation using Yahoo Finance
  - The only component allowed to directly use the Yahoo Finance SDK

---

### MarketDataService

Implement a service responsible for:

- Provider selection
- Response normalization
- Data validation
- Redis caching of frequently requested quotes
- Returning a provider-independent interface to the rest of the application

Business logic must **never import Yahoo Finance directly**.

---

### Background Processing

Implement:

- Celery worker
- Redis task broker
- Scheduled OHLCV ingestion task

This becomes the first production use of the application's background-processing stack.

---

### Database

Create the following tables:

- `stocks`
- `market_data`

Also implement:

- `StockRepository`
- `MarketDataRepository`

using the repository pattern established in Phase 2.

---

# Folder(s) Affected

```text
backend/app/services/market_data/
backend/app/api/v1/market_data/
backend/app/domain/models/
backend/app/domain/schemas/
backend/app/infrastructure/database/repositories/
backend/app/tasks/
backend/external/        (Yahoo Finance wrapper)
```

---

# Services Implemented

- `MarketDataService`
- `YahooFinanceProvider`

---

# APIs Introduced

### Get latest market quote

```http
GET /api/v1/market-data/{symbol}
```

---

### Get historical OHLCV data

```http
GET /api/v1/market-data/history/{symbol}
```

---

### Get supported market indices

```http
GET /api/v1/market-data/indices
```

---

### Get options chain

```http
GET /api/v1/market-data/options/{symbol}
```

---

# Database Tables Introduced

- `stocks`
- `market_data`

---

# External Integrations

- Yahoo Finance API

---

# Testing Requirements

## Unit Tests

- Provider interface contract (mocked Yahoo Finance responses)
- Data normalization
- Data validation
- Missing value handling
- Duplicate record detection
- Timestamp validation
- Redis cache behavior

---

## Integration Tests

- Celery ingestion task
- Repository persistence
- Database writes into `market_data`

---

## API Tests

Verify:

- Latest quote endpoint
- Historical data endpoint
- Indices endpoint
- Options chain endpoint
- Invalid symbol handling
- Authentication protection
- Cache hit/miss behavior

---

# Completion Checklist

- [ ] Live quote data retrievable through the API for at least one real symbol.
- [ ] Historical OHLCV data retrievable through the API.
- [ ] Indices endpoint returns normalized market index data.
- [ ] Options chain endpoint returns normalized options data.
- [ ] Data validation rejects malformed, duplicate, or invalid records before persistence.
- [ ] Redis caching is implemented for frequently requested market data.
- [ ] Background ingestion task runs on schedule and is independently testable.
- [ ] `stocks` and `market_data` tables are created via Alembic migration.
- [ ] Business logic never imports the Yahoo Finance SDK directly—only through `MarketDataService`.
- [ ] All unit, integration, and API tests pass.
- [ ] Ruff, MyPy, Pytest, and GitHub Actions pass successfully.

---

# Estimated Complexity

**Medium**

# Estimated Implementation Effort

**~3 days**

## Phase 5 – Feature Engineering Layer

**Goal:** Build the reusable indicator pipeline (RSI, EMA, SMA, MACD, VWAP, ATR, ADX, Bollinger Bands, Ichimoku, OBV, Volume Profile, PCR, returns, rolling stats) that transforms raw `market_data` into a standardized feature set for forecasting.

**Why this phase comes now:** Forecasting models (Phase 6) require engineered features as input; this layer must exist and be independently correct/tested first, since numerical bugs here would silently corrupt every downstream prediction.

**Dependencies:** Phase 4 (`market_data`).

**Deliverables:**

- `backend/app/services/feature_engineering/` with one indicator module per computation family, composed via a `FeaturePipeline` class.
- Pandas/Polars/NumPy-based implementation per §6.
- Standardized feature-vector output schema consumed uniformly by all forecasting wrappers.
- API endpoint to fetch computed features for a symbol (used by the frontend Stock Analysis page later, and internally by Forecasting).

**Folder(s) affected:** `backend/app/services/feature_engineering/`.

**Services implemented:** `FeaturePipeline` (and per-indicator functions).

**APIs introduced:** internal service only in this phase (no new public endpoint required beyond what's reused by later API phases); optionally `GET /api/v1/market-data/{symbol}/features` if desired for early frontend testing (documented as internal-first).

**Database tables introduced:** none new (features computed on demand / cached in Redis; persisted feature snapshots optionally added to `market_data` metadata).

**External integrations:** none.

**Testing requirements:** unit tests per indicator against known reference values (golden-value tests); property tests for edge cases (insufficient history, NaNs, zero volume); performance benchmark for pipeline execution time on a large OHLCV series.

**Completion checklist:**

- [ ] Every listed indicator implemented and unit-tested against a known reference dataset.
- [ ] Pipeline runs end-to-end on real ingested data from Phase 4 without errors.
- [ ] Output schema is documented and stable (versioned) for forecasting consumption.
- [ ] No indicator computation duplicated across modules.

**Estimated complexity:** Medium.
**Estimated implementation effort:** 3–4 days.

---



#### Model Registry

The Model Registry provides a centralized mechanism for registering, discovering, loading, and managing all forecasting models used within TradeAI. Rather than allowing downstream services to instantiate forecasting models directly, every model must first be registered with the registry. This ensures loose coupling, simplifies model replacement, and enables future support for model versioning and dynamic model selection.

**Responsibilities**

- Register forecasting models
- Load model instances
- Track model versions
- Return available models
- Validate model health
- Support dynamic model selection
- Expose active model metadata

The `ForecastService` communicates exclusively with the `ModelRegistry` rather than directly interacting with individual forecasting models.

#### Architecture

```text
ForecastService
        │
        ▼
 ModelRegistry
        │
 ┌──────┼──────────┐
 ▼      ▼          ▼
TimesFM Chronos LightGBM
        │
        ▼
 Prediction
```

---



#### Prompt Management

TradeAI relies on multiple AI agents, Retrieval-Augmented Generation (RAG), and LLM providers. To maintain consistency, all prompts must be centrally managed rather than embedded directly within services or agents.

A dedicated `PromptService` stores, versions, and retrieves prompts for every AI workflow.

**Prompt Categories**

- System Prompts
- Agent Prompts
- Research Prompts
- Reflection Prompts
- Evaluation Prompts
- RAG Context Templates
- Chat Prompts

**Responsibilities**

- Centralized prompt storage
- Prompt versioning
- Dynamic prompt loading
- Prompt validation
- Reusable prompt templates
- Environment-specific prompt overrides

No prompt should be hardcoded inside business logic or agent implementations.

---



## Phase 6 – Forecasting Layer (Model Wrappers)

**Goal:** Implement `BaseForecastModel` and the first two concrete model wrappers — `XGBoostService` and `LightGBMService` (feature-driven, fastest to stand up) — with the standardized prediction schema from §10. All forecasting models, including XGBoost, LightGBM, TimesFM, Chronos, and PatchTST, are implemented behind the `BaseForecastModel` interface and registered through the `ModelRegistry`. This allows the Ensemble Engine to dynamically select and combine forecasting models without coupling to specific implementations.

**Why this phase comes now:** Feature Engineering must exist first. Starting with tree-based models (rather than TimesFM/Chronos, which need heavier model-serving infrastructure) keeps this phase independently shippable while still exercising the full wrapper interface (`initialize/predict/train/shutdown`) that later models must also satisfy.

**Dependencies:** Phase 5 (feature vectors).

### Deliverables

- `ModelRegistry` responsible for registering, loading, versioning, and exposing forecasting models.
- `BaseForecastModel` abstract interface.
- `XGBoostService`
- `LightGBMService`
- `TimesFMService`
- `ChronosService`
- `PatchTSTService`
- `ForecastService`
- Standardized prediction schema.

**Folder(s) affected:** `backend/app/services/forecasting/`, `backend/app/api/v1/forecast/`, `backend/app/domain/models/` (prediction, model_output).

**Services implemented:** `ForecastService`, `XGBoostService`, `LightGBMService`.

**APIs introduced:**

- `POST /api/v1/forecast/predict`
- `GET /api/v1/forecast/models`
- `GET /api/v1/forecast/history/{symbol}`

**Database tables introduced:** `predictions`, `model_outputs`.

**External integrations:** none (self-hosted models); model weights stored locally/in model-storage volume.

**Testing requirements:** unit tests for model initialization/predict/train/shutdown lifecycle with deterministic seeds; schema-validation tests for standardized output; API tests for `/predict`, `/models`, `/history/{symbol}`; explainability output tested for at least one symbol.

**Completion checklist:**

- [ ] Both model wrappers implement the identical interface and produce schema-conformant output.
- [ ] `/forecast/predict` returns a real prediction end-to-end from live market data.
- [ ] Model version and input metadata are logged with every prediction (traceability, per §7).
- [ ] Business/API layers never reference `xgboost`/`lightgbm` directly — only through the service wrappers.

**Estimated complexity:** High.
**Estimated implementation effort:** 4–5 days.

---



## Phase 7 – Ensemble Engine

**Goal:** Combine multiple model outputs into a single standardized ensemble prediction using a configurable strategy (starting with weighted averaging and confidence-weighted aggregation).

**Why this phase comes now:** Requires at least two forecasting models to be meaningful (satisfied by Phase 6). Must exist before Decision Engine/Agents, which consume a single unified forecast rather than raw per-model output.

**Dependencies:** Phase 6 (≥2 model wrappers).

**Deliverables:**

- `EnsembleEngine` service supporting pluggable strategies (`weighted_average`, `confidence_weighted`; majority voting and dynamic selection stubbed for future config-only extension).
- External (non-hardcoded) ensemble configuration (weights, strategy selection) per §11.
- Standardized ensemble output schema with per-model contribution metadata.
- Partial-failure handling (ensemble still produced if one model fails, provided enough models remain).

**Folder(s) affected:** `backend/app/services/ensemble/`.

**Services implemented:** `EnsembleEngine`.

**APIs introduced:** none new (folded into `/api/v1/forecast/predict` response as an `ensemble` field, or exposed as `POST /api/v1/forecast/predict?ensemble=true` — documented choice; no separate public route required by §21 spec).

**Database tables introduced:** none new (`model_outputs` from Phase 6 extended with contribution metadata columns, or a dedicated `ensemble_outputs` table if contribution auditability requires it).

**External integrations:** none.

**Testing requirements:** unit tests for each ensemble strategy against synthetic model outputs; test for graceful degradation when one model wrapper raises; determinism test (same inputs → same ensemble output).

**Completion checklist:**

- [ ] Ensemble output produced from ≥2 live model predictions.
- [ ] Strategy is swappable via configuration without code changes.
- [ ] Contribution metadata is stored and retrievable for auditability.
- [ ] Ensemble degrades gracefully rather than failing when one model errors.

**Estimated complexity:** Medium.
**Estimated implementation effort:** 2 days.

---



## Phase 8 – RAG Layer

**Goal:** Build the full document ingestion → chunking → embedding → vector storage → retrieval pipeline against Qdrant (with FAISS as the local-dev alternative), starting with one knowledge source (financial news) to prove the pipeline before adding others.

**Why this phase comes now:** Multi-Agent System (Phase 9) depends on RAG for News/Fundamental/Macro agents. RAG is independent of forecasting, so it can be built in parallel conceptually, but is sequenced here because agents need it ready first.

**Dependencies:** Phase 2 (database, for `documents` metadata table), Phase 1 (config for vector DB URL).

**Deliverables:**

- `backend/app/infrastructure/vector_db/`: Qdrant client wrapper + FAISS local fallback, both behind a common interface.
- Document ingestion pipeline: source collection → validation → text extraction → cleaning → metadata generation → chunking → embedding → vector storage → index update (per §12).
- `EmbeddingService` (provider-agnostic, versioned embeddings).
- Retrieval pipeline: query embedding → similarity search (top-K) → ranking/filtering → context package assembly with citations.
- One ingestion source wired end-to-end: financial news (via a news API or RSS/scraper module in `backend/external/`).
- `documents` (metadata only) and `retrieval_logs` tables + repositories.

**Folder(s) affected:** `backend/app/services/rag/`, `backend/app/infrastructure/vector_db/`, `backend/app/api/v1/rag/`, `backend/external/` (news source client).

**Services implemented:** `DocumentIngestionService`, `EmbeddingService`, `RetrievalService`, `RAGService` (facade).

**APIs introduced:**

- `POST /api/v1/rag/search`
- `POST /api/v1/rag/query`
- `GET /api/v1/rag/documents`

**Database tables introduced:** `documents`, `retrieval_logs`.

**External integrations:** Qdrant (or FAISS locally); a financial news source/API.

**Testing requirements:** unit tests for chunking strategy (no mid-sentence/table splits); integration tests for embedding → store → retrieve round trip; retrieval relevance/precision spot checks; citation-generation tests; latency benchmark for retrieval.

**Completion checklist:**

- [ ] A real news article can be ingested, embedded, stored, and retrieved via semantic search with correct citation metadata.
- [ ] Vector storage is decoupled from the LLM provider (interface-based).
- [ ] `retrieval_logs` capture query, results, and latency for every retrieval.
- [ ] FAISS local mode works without requiring a running Qdrant instance (dev convenience).

**Estimated complexity:** High.
**Estimated implementation effort:** 5 days.

---



## Phase 9 – Multi-Agent System

**Goal:** Implement `BaseAgent`, the LangGraph orchestration graph, and all eleven agents (Coordinator, Market Data, Technical Analysis, Fundamental Analysis, News Analysis, Macro Analysis, Portfolio Manager, Risk Manager [advisory], Decision, Execution, Reflection), each producing structured (non-free-form) output.

**Why this phase comes now:** Requires Feature Engineering, Forecasting/Ensemble, and RAG to all exist, since agents consume all three. This is the largest single phase; it is broken into sequenced sub-deliverables below but shipped as one phase because the agents are tightly interdependent through the LangGraph state.

**Dependencies:** Phase 5 (features), Phase 7 (ensemble predictions), Phase 8 (RAG).

**Deliverables:**

- `BaseAgent` ABC + `BaseLLMProvider` interface (initialize/complete/stream/shutdown) with one concrete OpenAI-compatible provider implementation.
- LangGraph workflow: sequencing, conditional branching, retry logic, parallel execution, shared state, failure recovery (per §13).
- Structured agent-to-agent communication schema (`agent`, `summary`, `confidence`, `signals`, `supporting_data`).
- Concrete agents:
  - `MarketDataAgent` (wraps Phase 4 service)
  - `TechnicalAnalysisAgent` (wraps Phase 5/6/7 outputs)
  - `FundamentalAnalysisAgent` (wraps Phase 8 RAG for filings/reports)
  - `NewsAnalysisAgent` (wraps Phase 8 RAG for news)
  - `MacroAnalysisAgent` (wraps Phase 8 RAG for macro sources)
  - `PortfolioManagerAgent` (initially operates on stub/paper portfolio data until Phase 12 lands; interface finalized here, wired fully in Phase 12)
  - `RiskManagerAgent` (advisory only — produces risk assessment, does **not** approve trades; deterministic approval remains exclusively the Risk Engine's job, built in Phase 11)
  - `DecisionAgent` (structural synthesis only in this phase; full Decision Engine logic detailed in Phase 10)
  - `ExecutionAgent` (order-translation logic built here; actual broker calls wired in Phase 14)
  - `ReflectionAgent` (full logic wired once Trade Logger/RLAIF exist — Phases 13/16; agent shell and interface built here)
  - `CoordinatorAgent` (orchestrates the above via LangGraph; performs no analysis itself)
- Short-term memory (conversation/workflow state) and long-term memory access mediated through a dedicated `MemoryService`.
- `agent_logs` table + repository.

**Folder(s) affected:** `backend/app/services/agents/` (one file per agent), `backend/app/infrastructure/llm/`, `backend/app/api/v1/agents/`.

**Services implemented:** `CoordinatorAgent` + 10 specialized agents, `MemoryService`, `BaseLLMProvider` implementation.

**APIs introduced:**

- `POST /api/v1/agents/analyze`
- `GET /api/v1/agents/status`
- `GET /api/v1/agents/workflow/{id}`

**Database tables introduced:** `agent_logs`.

**External integrations:** OpenAI-compatible LLM API.

**Testing requirements:** unit tests per agent (input handling, output structure, error recovery) as required by §23; LangGraph workflow tests for sequencing/branching/retry; contract tests ensuring every agent conforms to the structured-output schema; test confirming `RiskManagerAgent` output is advisory-only and never triggers execution.

**Completion checklist:**

- [ ] `POST /api/v1/agents/analyze` runs the full LangGraph workflow for a symbol and returns aggregated structured findings.
- [ ] Every agent is independently unit-testable and replaceable without touching others.
- [ ] Coordinator performs no financial analysis itself (verified by code review / test).
- [ ] Risk Manager Agent output is clearly separated from (and cannot substitute for) Risk Engine approval.

**Estimated complexity:** High.
**Estimated implementation effort:** 7–9 days.

---



## Phase 10 – Decision Engine

**Goal:** Implement the Decision Engine that synthesizes forecasting, technical, fundamental, news, macro, and (stubbed) portfolio/risk inputs into a final Buy/Sell/Hold recommendation with confidence, forecast price, risk score, evidence, and reasoning.

**Why this phase comes now:** Requires the Ensemble Engine and the full Multi-Agent System's structured outputs as direct inputs. Precedes Risk Engine because the Decision Engine produces the *proposed* trade that the Risk Engine will later validate.

**Dependencies:** Phase 7 (ensemble), Phase 9 (agent outputs).

**Deliverables:**

- `DecisionEngine` service combining `DecisionAgent` output with ensemble and agent data into the final standardized recommendation schema from §4/§9 Stage 8.
- `decision_logs` table + repository, storing recommendation, evidence, and agent consensus.
- Research/analysis API surface (`/research/*`) built on top of the Decision Engine + RAG + agents.

**Folder(s) affected:** `backend/app/services/decision/`, `backend/app/api/v1/research/`.

**Services implemented:** `DecisionEngine`.

**APIs introduced:**

- `POST /api/v1/research/stock`
- `POST /api/v1/research/company`
- `POST /api/v1/research/news`

**Database tables introduced:** `decision_logs`.

**External integrations:** none new (reuses Phases 6–9 integrations).

**Testing requirements:** unit tests for recommendation synthesis logic with mocked agent/ensemble inputs; integration test running the full pipeline (market data → features → forecast → ensemble → agents → decision) for one symbol; test that Decision Agent never triggers execution directly.

**Completion checklist:**

- [ ] `/research/stock` returns a full recommendation (Buy/Sell/Hold, confidence, forecast price, risk score, evidence, reasoning) for a real symbol end-to-end.
- [ ] Decision output is fully traceable back to contributing model/agent outputs via `decision_logs`.
- [ ] No trade execution occurs as a side effect of calling the Decision Engine.

**Estimated complexity:** High.
**Estimated implementation effort:** 3–4 days.

---



## Phase 11 – Risk Engine

**Goal:** Implement the deterministic Risk Engine — the sole authority for trade approval — covering position sizing, portfolio exposure, stop-loss validation, market/liquidity/execution risk checks, configurable user risk profiles, and risk scoring.

**Why this phase comes now:** Must exist before any trade can be validated or executed. It is intentionally built independent of forecasting models and agents (per §16), consuming only the Decision Engine's proposed trade plus (initially minimal, stubbed) portfolio state — full portfolio integration follows immediately in Phase 12.

**Dependencies:** Phase 10 (proposed trade object).

**Deliverables:**

- `RiskEngine` service implementing all checks from §16: position risk, portfolio risk, market risk, liquidity risk, execution risk.
- Configurable `RiskProfile` (Conservative/Moderate/Aggressive/Custom) with user-defined limits (max allocation, max position size, max drawdown, risk-to-reward, daily loss limit).
- Deterministic risk-score calculation and trade validation rule engine, with "default to reject when uncertain" behavior per §16.
- `risk_assessments` table + repository.
- Risk Management API.

**Folder(s) affected:** `backend/app/services/risk/`, `backend/app/api/v1/risk/`.

**Services implemented:** `RiskEngine`.

**APIs introduced:**

- `POST /api/v1/risk/evaluate`
- `GET /api/v1/risk/report`

**Database tables introduced:** `risk_assessments`.

**External integrations:** none (deliberately independent of brokers/LLMs).

**Testing requirements:** unit tests for every risk category (position, portfolio, market, liquidity, execution) with both passing and failing scenarios; unit tests for each configurable risk profile; test verifying "reject on uncertainty" default; regression tests locking in critical thresholds.

**Completion checklist:**

- [ ] Every check category from §16 is implemented and independently unit-tested.
- [ ] A proposed trade from the Decision Engine is correctly approved or rejected with a stored, explainable reason.
- [ ] Risk Engine has zero direct dependency on forecasting models, agents, or brokers.
- [ ] User risk profiles are configurable data, not hardcoded constants.

**Estimated complexity:** High.
**Estimated implementation effort:** 4–5 days.

---



## Phase 12 – Portfolio Engine (Data Model & Paper Trading Path)

**Goal:** Implement portfolio, holdings, allocation/diversification analysis, performance tracking, and trade-impact analysis, operating first against internally-managed **paper trading** state (no live broker required yet).

**Why this phase comes now — and ordering note:** `SYSTEM_DESIGN.md`'s suggested top-level ordering places Portfolio Engine before Broker Layer, yet also states the Portfolio Engine "continuously synchronizes with the Broker Layer." To avoid a circular dependency, this roadmap splits that responsibility: this phase builds the full portfolio data model, calculations, and trade-impact analysis against paper-trading holdings (which the Risk Engine and Decision Engine can already use); Phase 14 (Broker Layer) later adds **live** synchronization behind the *same* `PortfolioEngine` interface, so no portfolio logic is rewritten.

**Dependencies:** Phase 11 (risk assessment references portfolio state), Phase 2 (database).

**Deliverables:**

- `portfolios` and `holdings` tables + repositories.
- `PortfolioEngine` service: holdings management, asset allocation analysis, diversification analysis, performance tracking, exposure monitoring, trade-impact analysis, portfolio recommendations (advisory).
- Paper-trading portfolio state manager (virtual cash balance, simulated fills) satisfying the same interface that live broker sync will later implement.
- Wiring of `PortfolioManagerAgent` (Phase 9 stub) and `RiskEngine` (Phase 11) to real portfolio data.
- Portfolio API.

**Folder(s) affected:** `backend/app/services/portfolio/`, `backend/app/api/v1/portfolio/`.

**Services implemented:** `PortfolioEngine`.

**APIs introduced:**

- `GET /api/v1/portfolio`
- `GET /api/v1/portfolio/holdings`
- `GET /api/v1/portfolio/performance`
- `POST /api/v1/portfolio/rebalance`

**Database tables introduced:** `portfolios`, `holdings`.

**External integrations:** none yet (paper trading is internal; live broker sync deferred to Phase 14).

**Testing requirements:** unit tests for allocation/diversification/performance calculations against known fixture portfolios; test for trade-impact analysis on a proposed trade; integration test wiring `PortfolioManagerAgent` and `RiskEngine` to real portfolio data.

**Completion checklist:**

- [ ] A user has a paper-trading portfolio with holdings, cash balance, and computed performance metrics.
- [ ] Risk Engine's portfolio-risk checks now use real (paper) portfolio state instead of stubs.
- [ ] Trade-impact analysis correctly previews allocation/exposure changes before a hypothetical trade.
- [ ] Portfolio Engine has no direct dependency on any specific broker SDK.

**Estimated complexity:** Medium.
**Estimated implementation effort:** 3–4 days.

---



## Phase 13 – Trade Logger

**Goal:** Implement the append-only, auditable Trade Logger recording every stage of a trade's lifecycle — proposed, risk-evaluated (approved/rejected), submitted, confirmed/failed — linked to predictions, agent outputs, risk decisions, and portfolio snapshots.

**Why this phase comes now:** Requires Decision Engine, Risk Engine, and Portfolio Engine outputs to have something meaningful to log, and must exist *before* the Broker Layer (Phase 14) so that every broker interaction is logged from its very first execution, not retrofitted.

**Dependencies:** Phase 10, Phase 11, Phase 12.

**Deliverables:**

- `TradeLogger` service with append-only write semantics and safe-retry behavior when persistence is briefly unavailable (per §15).
- `trades` and `orders` tables + repositories (introduced here since Trade Logger is their primary writer; extended for real broker fields in Phase 14).
- Linking logic: trade record ↔ prediction ID ↔ decision ID ↔ risk assessment ID ↔ portfolio snapshot reference.

**Folder(s) affected:** `backend/app/services/trade_logger/`.

**Services implemented:** `TradeLogger`.

**APIs introduced:** none new in this phase (logger is invoked internally by Decision/Risk/Portfolio flows); trade-history read endpoints are introduced in Phase 14 alongside the Broker Layer, once real executions exist to list.

**Database tables introduced:** `trades`, `orders`.

**External integrations:** none.

**Testing requirements:** unit tests confirming a rejected trade is still logged; integration test for the full logging chain (proposed → rejected) and (proposed → approved, pending broker) using Phase 12 paper-trading portfolio; test for retry-safe persistence under simulated DB unavailability.

**Completion checklist:**

- [ ] Every proposed trade — approved or rejected — produces an immutable log entry.
- [ ] Log entries are fully linkable to prediction, decision, and risk-assessment records.
- [ ] Logging failures never block the Decision/Risk pipeline (verified by test).
- [ ] Trade Logger has zero dependency on broker SDKs or forecasting models.

**Estimated complexity:** Medium.
**Estimated implementation effort:** 2 days.

---



## Phase 14 – Broker Layer (Paper & Live Trading)

**Goal:** Implement the common broker interface, wire the Portfolio Engine's paper-trading path to a formal `PaperBrokerAdapter`, and add the first live adapter (`UpstoxAdapter`), followed by `ZerodhaAdapter`, both behind the same interface. Extend Portfolio Engine with real broker synchronization.

**Why this phase comes now:** Requires Decision Engine, Risk Engine, Portfolio Engine, and Trade Logger to all exist, since a broker order is the terminal step of that whole pipeline.

**Dependencies:** Phase 13 (logging), Phase 12 (portfolio), Phase 11 (risk approval gate).

**Deliverables:**

- `BrokerInterface` ABC (`initialize`, `authenticate`, `refresh_session`, `place_order`, `modify_order`, `cancel_order`, `get_order_status`, `get_positions`, `get_holdings`, `get_account_balance`, `get_order_history`, `disconnect`).
- `PaperBrokerAdapter` (formalizes Phase 12's simulated execution behind the same interface as live brokers).
- `UpstoxAdapter`, `ZerodhaAdapter` concrete implementations with OAuth-based auth, token refresh, and secure credential storage.
- `BrokerService` orchestrating adapter selection, order lifecycle, and error handling (auth failures, rate limits, rejections, timeouts).
- Portfolio Engine extended with live synchronization (holdings, positions, cash, margin, realized/unrealized P&L) from the active broker adapter, using the interface defined in Phase 12.
- `broker_accounts`, `broker_sessions` tables + repositories.
- Trading and Order Management APIs.

**Folder(s) affected:** `backend/app/services/broker/`, `backend/app/api/v1/trades/`, `backend/app/api/v1/orders/`.

**Services implemented:** `BrokerService`, `PaperBrokerAdapter`, `UpstoxAdapter`, `ZerodhaAdapter`.

**APIs introduced:**

- `POST /api/v1/trades/paper`
- `POST /api/v1/trades/live`
- `GET /api/v1/trades/history`
- `GET /api/v1/trades/{trade_id}`
- `POST /api/v1/orders`
- `PUT /api/v1/orders/{id}`
- `DELETE /api/v1/orders/{id}`
- `GET /api/v1/orders`

**Database tables introduced:** `broker_accounts`, `broker_sessions`.

**External integrations:** Upstox API, Zerodha (Kite Connect) API.

**Testing requirements:** broker tests run only against sandbox/paper environments per §23 (never live trading in automated tests); unit tests for the interface contract across all three adapters; integration tests for full order lifecycle (proposed → risk-approved → submitted → confirmed → logged → portfolio updated) using the paper adapter; auth/token-refresh tests mocked against broker sandbox APIs.

**Completion checklist:**

- [ ] Paper trading executes a full order lifecycle end-to-end using the same interface as live brokers.
- [ ] Upstox and Zerodha adapters authenticate, place, and query orders against sandbox environments.
- [ ] Portfolio Engine reflects real broker-synchronized state when a live/sandbox account is connected.
- [ ] No trade reaches a broker adapter without prior Risk Engine approval (enforced in code, verified by test).
- [ ] Credentials are never hardcoded or logged in plaintext.

**Estimated complexity:** High.
**Estimated implementation effort:** 6–7 days.

---



## Phase 15 – Notification Service

**Goal:** Implement the Notification Service delivering trade confirmations, risk alerts, AI recommendations, and system events to the frontend via in-app notifications (email/push deferred to Future Enhancements).

**Why this phase comes now:** Depends on Risk Engine, Broker Layer, Decision Engine, Portfolio Engine, and Trade Logger as event sources — all now exist. Placed just before the RLAIF/frontend phases so the frontend (Phase 17) can render notifications from day one.

**Dependencies:** Phase 11, Phase 12, Phase 13, Phase 14.

**Deliverables:**

- `NotificationService` consuming events from Risk Engine, Broker Layer, Decision Engine, Portfolio Engine, Trade Logger via an internal event/pub-sub pattern (decoupled — never blocking the emitting service).
- User notification-preference storage and enforcement (critical alerts always recorded regardless of preference).
- `notifications` table + repository.
- Notification read/delivery API surface (folded into user-facing endpoints consumed by the frontend in Phase 17/18).

**Folder(s) affected:** `backend/app/services/notification/`.

**Services implemented:** `NotificationService`.

**APIs introduced:** `GET /api/v1/notifications`, `PUT /api/v1/notifications/{id}/read` (introduced here as the minimal surface needed; full notification UI wiring happens in Phase 17).

**Database tables introduced:** `notifications`.

**External integrations:** none in this phase (email/push are explicitly future work per §18).

**Testing requirements:** unit tests confirming notification delivery never blocks the emitting service (simulated slow/broken delivery channel); tests for preference enforcement vs. critical-alert override; integration test verifying a rejected trade and a filled order both produce correct notification records.

**Completion checklist:**

- [ ] Trade confirmations, risk alerts, and AI recommendations all produce in-app notification records.
- [ ] Notification delivery failures never block or delay trading/AI workflows.
- [ ] Critical alerts are always recorded even when user preferences would otherwise suppress delivery.
- [ ] Service has zero dependency on Botpress or broker SDKs (per §18 design principle).

**Estimated complexity:** Low.
**Estimated implementation effort:** 1.5–2 days.

---



## Phase 16 – RLAIF & Continuous Learning Layer

**Goal:** Implement the Reflection Agent's full post-trade analysis, the structured learning-record pipeline, and performance-metric tracking (win rate, profit factor, Sharpe/Sortino, drawdown, confidence calibration, agent agreement, retrieval relevance).

**Why this phase comes now:** Requires completed trades (Trade Logger/Broker Layer), portfolio state (Portfolio Engine), and RAG/ensemble outputs — all now available — to generate meaningful learning records.

**Dependencies:** Phase 14 (completed trades), Phase 12 (portfolio state), Phase 9 (Reflection Agent shell), Phase 7/8 (ensemble & RAG outputs to record).

**Deliverables:**

- Full `ReflectionAgent` implementation: post-trade review, prediction-quality/reasoning-quality/evidence-quality/risk-quality scoring, overall decision score.
- `LearningPipeline` service assembling the full learning record (market snapshot, features, forecasts, ensemble prediction, RAG context, agent outputs, decision, executed order, outcome, portfolio state, reflection).
- `learning_records` and `reflection_logs` tables + repositories.
- Performance-metrics aggregation (win rate, profit factor, Sharpe, Sortino, max drawdown, confidence calibration, agent agreement, retrieval relevance) exposed via API.
- Explicit safeguards: production models are never auto-retrained; learning data is versioned and immutable.

**Folder(s) affected:** `backend/app/services/rlaif/`.

**Services implemented:** `ReflectionAgent` (finalized), `LearningPipeline`.

**APIs introduced:**

- `GET /api/v1/learning/performance`
- `GET /api/v1/learning/reflections`

**Database tables introduced:** `learning_records`, `reflection_logs`.

**External integrations:** none new.

**Testing requirements:** unit tests for reflection scoring logic against fixture trade outcomes; integration test generating a full learning record from an actual completed paper trade; test confirming historical learning data is never overwritten; test confirming no automatic model retraining is triggered.

**Completion checklist:**

- [ ] A completed paper trade produces a full, structured learning record with reflection scores.
- [ ] Performance metrics (win rate, Sharpe, drawdown, etc.) are computable and exposed via API.
- [ ] Learning records are immutable/versioned and independently auditable.
- [ ] No code path allows a production model to retrain itself automatically from live data.

**Estimated complexity:** Medium.
**Estimated implementation effort:** 3–4 days.

---



## Phase 17 – Frontend Foundation (Dashboard, Auth, Core Shell)

**Goal:** Build the Next.js application shell — authentication screens, layout/navigation, and the Dashboard module — consuming the backend APIs completed so far (auth, market data, portfolio, notifications).

**Why this phase comes now:** All backend functionality a baseline dashboard needs (auth, portfolio, market data, notifications) now exists. Frontend work is sequenced after backend core loops so the UI is built against real, stable contracts rather than mocks that later drift.

**Dependencies:** Phase 3 (auth), Phase 4 (market data), Phase 12 (portfolio), Phase 15 (notifications).

**Deliverables:**

- Next.js + TypeScript + Tailwind app shell: routing, layout, protected-route handling.
- Authentication screens (register/login/logout/password reset UI) wired to `/api/v1/auth/*`.
- API communication layer (typed client) in `frontend/lib/`.
- Dashboard module: market summary, indices, watchlist overview (stub until Phase 18), portfolio snapshot, daily P&L, recent recommendations, active positions, notifications panel.
- Global loading/error-state conventions.

**Folder(s) affected:** `frontend/app/`, `frontend/components/`, `frontend/lib/`, `frontend/public/`.

**Services implemented:** none (frontend consumes existing backend services only).

**APIs introduced:** none new (frontend consumes Phases 3, 4, 12, 15 APIs).

**Database tables introduced:** none.

**External integrations:** none.

**Testing requirements:** Vitest unit tests for components; React Testing Library tests for auth forms and dashboard rendering; Playwright E2E test for register → login → view dashboard.

**Completion checklist:**

- [ ] User can register, log in, and view a populated dashboard with real backend data.
- [ ] Protected routes correctly redirect unauthenticated users.
- [ ] Frontend never talks to the database or external services directly — only the backend API.
- [ ] Responsive layout verified on desktop/tablet/mobile widths.

**Estimated complexity:** Medium.
**Estimated implementation effort:** 4–5 days.

---



## Phase 18 – Frontend Feature Modules

**Goal:** Build the remaining core frontend modules: AI Research Workspace, Stock Analysis page, Portfolio Management, Trading Terminal, Watchlists, Analytics Dashboard, User Settings.

**Why this phase comes now:** Depends on the Dashboard shell (Phase 17) plus the backend research/forecast/agent, trading, and learning APIs (Phases 6, 9, 10, 14, 16), all of which are now complete.

**Dependencies:** Phase 17, Phase 6, Phase 9, Phase 10, Phase 14, Phase 16.

**Deliverables:**

- Stock Analysis page: price charts, indicators, forecast + confidence, AI recommendation, risk assessment, company overview, news, RAG documents, multi-agent reasoning display, historical accuracy.
- AI Research Workspace: company/financial-statement analysis, RAG-powered document search, multi-agent reasoning visualization, citations.
- Portfolio Management module: holdings, allocation, sector distribution, performance, P&L, diversification, health score.
- Trading Terminal: paper/live order placement, modification, cancellation, positions, order history, execution status.
- Watchlists: multiple lists, price alerts, AI recommendations, news, portfolio integration.
- Analytics Dashboard: portfolio growth, win rate, profit factor, Sharpe/Sortino, drawdown, prediction accuracy, model/agent comparison, learning trends.
- User Settings: risk profile, preferred brokers, notification preferences, theme, connected broker accounts.
- `watchlists` table + repository and corresponding minimal API (`GET/POST /api/v1/watchlist`, per §8 naming conventions) added here to support this module.

**Folder(s) affected:** `frontend/app/`, `frontend/components/`; backend: `backend/app/api/v1/watchlist/` (new), `backend/app/services/` (watchlist service).

**Services implemented:** `WatchlistService` (backend, new); frontend modules only otherwise.

**APIs introduced:** `GET /api/v1/watchlist`, `POST /api/v1/watchlist`, `PUT/DELETE /api/v1/watchlist/{id}` (backend addition required to support this frontend module — the only new backend surface in this phase).

**Database tables introduced:** `watchlists`.

**External integrations:** none new.

**Testing requirements:** component tests for every module; Playwright E2E flows for: stock research, portfolio review, paper trade placement, watchlist management (all listed explicitly in §23 E2E examples); accessibility checks.

**Completion checklist:**

- [ ] Every module listed above renders real backend data end-to-end.
- [ ] A user can research a stock, view AI reasoning with citations, place a paper trade, and see it reflected in portfolio/analytics.
- [ ] Watchlists persist and sync across sessions.
- [ ] All trading actions in the Terminal are validated server-side by the Risk Engine (frontend cannot bypass it).

**Estimated complexity:** High.
**Estimated implementation effort:** 7–8 days.

---



## Phase 19 – Chat API & Botpress Integration

**Goal:** Implement the Chat API (message, stream, conversation history) as a conversational gateway into the existing Decision/RAG/Agent backend, and connect the Botpress AI Assistant to it as the primary conversational frontend surface.

**Why this phase comes now:** The Chat API is a *thin gateway* — it has nothing to forward requests to until Research, RAG, Agents, and Decision Engine are complete, and nothing meaningful to show until the frontend modules that present citations/tables/charts exist (Phase 18).

**Dependencies:** Phase 10 (Decision Engine/Research), Phase 8 (RAG), Phase 9 (Agents), Phase 18 (frontend rendering for tables/citations/charts).

**Deliverables:**

- Chat API: message handling, streaming (SSE or WebSocket), conversation persistence, deletion.
- `ChatService` translating chat messages into calls against Research/RAG/Agent/Portfolio/Trade services — the chatbot performs no forecasting/reasoning/trading logic itself, per §22.
- Botpress workspace configured to call the Chat API exclusively (no direct backend/database access from Botpress).
- Frontend Botpress Chat component: streaming responses, markdown, financial tables, embedded charts, citations, suggested follow-ups, conversation history.
- `conversations`/`chat_messages` tables + repositories.

**Folder(s) affected:** `backend/app/api/v1/chat/`, `backend/app/services/` (chat), `frontend/components/` (chat widget), `docker/` (Botpress service addition to compose).

**Services implemented:** `ChatService`.

**APIs introduced:**

- `POST /api/v1/chat/message`
- `POST /api/v1/chat/stream`
- `GET /api/v1/chat/conversations`
- `GET /api/v1/chat/conversations/{id}`
- `DELETE /api/v1/chat/conversations/{id}`

**Database tables introduced:** `conversations`, `chat_messages`.

**External integrations:** Botpress.

**Testing requirements:** chatbot tests per §23: message handling, API communication, conversation continuity, streaming, error handling, response formatting, citation rendering, multi-turn conversations; test confirming Botpress workflows contain no embedded business logic.

**Completion checklist:**

- [ ] A user can ask a natural-language question in the Botpress widget and receive a streamed, cited, grounded answer sourced from the real backend pipeline.
- [ ] Conversation history persists and is retrievable/deletable.
- [ ] Botpress never talks to the database, broker, or any service directly — only the Chat API.
- [ ] Multi-turn conversations correctly maintain context.

**Estimated complexity:** Medium.
**Estimated implementation effort:** 4 days.

---



## Phase 20 – Comprehensive Testing Hardening

**Goal:** Close testing gaps left as "sufficient for shipping the phase" with the full testing matrix from §23: full E2E suite, performance testing, security testing, regression suite, and coverage targets (business logic 90%+, API layer 85%+, utilities 90%+, critical workflows 100%).

**Why this phase comes now:** Every subsystem now exists; this phase is dedicated to closing gaps between "each phase individually tested" and "the whole system verified together," per the requirement that critical workflows have 100% coverage before production deployment.

**Dependencies:** all prior phases (0–19).

**Deliverables:**

- Full E2E suite (Playwright) covering every flow in §23 (registration/login, stock research, portfolio analysis, paper trade, live trade in sandbox, watchlist management, AI recommendation generation, RAG document retrieval).
- Performance test suite: API latency, forecast generation time, RAG retrieval latency, agent execution time, DB performance, frontend load time, concurrent-user load testing.
- Security test suite: authN/authZ, input validation, SQL injection, XSS, CSRF, JWT validation.
- Regression suite locking in critical areas: forecasting, trading, portfolio, auth, AI recommendations, broker communication.
- Coverage reporting wired into CI (Coverage.py + frontend coverage tooling) with enforced thresholds.
- Test-environment hardening: isolated test DB, mock broker APIs, mock market data, temporary vector DB, isolated auth config (no test ever touches production infra).

**Folder(s) affected:** `backend/tests/{unit,integration,e2e}`, `frontend` test directories, `.github/workflows/`.

**Services implemented:** none new (test infrastructure and mocks only).

**APIs introduced:** none.

**Database tables introduced:** none.

**External integrations:** none (mocked in this phase).

**Testing requirements:** this phase *is* the testing requirement — see Deliverables.

**Completion checklist:**

- [ ] Coverage thresholds met: business logic ≥90%, API layer ≥85%, utilities ≥90%, critical workflows 100%.
- [ ] Full E2E suite passes in CI against a disposable environment.
- [ ] Security test suite passes with no critical findings.
- [ ] CI blocks merges to `main` on any critical test failure.

**Estimated complexity:** Medium.
**Estimated implementation effort:** 5–6 days.

---



## Phase 21 – Deployment & Production Readiness

**Goal:** Finalize containerization, CI/CD, secrets management, monitoring/logging, backup/recovery, and security hardening for a production deployment, per §24.

**Why this phase comes now:** This is intentionally the final phase — deployment should only be automated and hardened once the full system (including its test suite) is complete and stable.

**Dependencies:** Phase 20 (fully tested system).

**Deliverables:**

- Production-ready `docker-compose.yml` (and/or Dockerfiles per service) for FastAPI, Next.js, PostgreSQL, Redis, Qdrant, background workers, reverse proxy (Nginx/Caddy), Botpress.
- GitHub Actions CI/CD pipeline: checkout → `uv` install → static analysis → unit/integration tests → security checks → Docker build → staging deploy → production deploy (manual approval gate).
- Secrets management approach (environment-based at minimum; dedicated secrets manager recommended) — no secrets in source control, verified by a CI secret-scanning step.
- Monitoring/logging: centralized structured logs; Prometheus/Grafana wiring (or documented as a near-term follow-up if solo-dev scope defers it) for API availability, latency, DB performance, inference time, background-job health, error rates.
- Backup & recovery procedures: automated PostgreSQL backups, vector DB backups, configuration backups, documented disaster-recovery/rollback steps.
- Security hardening: HTTPS everywhere, secure headers, firewall rules, network isolation, least-privilege access, dependency vulnerability scanning.
- Staging environment mirroring production for pre-release validation.

**Folder(s) affected:** `docker/`, `docker-compose.yml`, `.github/workflows/`, `docs/`.

**Services implemented:** none new (operational tooling only).

**APIs introduced:** none.

**Database tables introduced:** none.

**External integrations:** container registry, GitHub Actions, (optionally) Prometheus/Grafana.

**Testing requirements:** deployment smoke tests (staging environment boots and passes health checks); rollback-procedure dry run; backup/restore dry run.

**Completion checklist:**

- [ ] A single CI/CD pipeline takes a merged commit from test → staging → production with a manual production-approval gate.
- [ ] No secrets exist in source control (verified by automated scan).
- [ ] A documented, tested rollback procedure exists for every deployed component.
- [ ] Automated backups exist for PostgreSQL and the vector database, with a successful restore test on record.
- [ ] All external traffic is HTTPS-only; internal services are not directly internet-exposed.

**Estimated complexity:** Medium.
**Estimated implementation effort:** 4–5 days.

---



# Final Section



## 1. Dependency Graph

```
Phase 0  Project Foundation
   │
Phase 1  Configuration & Logging
   │
Phase 2  Database & Repositories ────────────────────────┐
   │                                                      │
Phase 3  Auth & API Skeleton                              │
   │                                                      │
Phase 4  Market Data Layer                                │
   │                                                      │
Phase 5  Feature Engineering                              │
   │                                                      │
Phase 6  Forecasting (Model Wrappers)                     │
   │                                                      │
Phase 7  Ensemble Engine                                  │
   │                              Phase 8  RAG Layer ◄────┘
   │                                     │
   └───────────────┬─────────────────────┘
                    ▼
           Phase 9  Multi-Agent System
                    │
           Phase 10 Decision Engine
                    │
           Phase 11 Risk Engine
                    │
           Phase 12 Portfolio Engine (paper)
                    │
           Phase 13 Trade Logger
                    │
           Phase 14 Broker Layer (paper + live; extends Portfolio sync)
                    │
           Phase 15 Notification Service
                    │
           Phase 16 RLAIF & Learning
                    │
           Phase 17 Frontend Foundation
                    │
           Phase 18 Frontend Feature Modules
                    │
           Phase 19 Chat API & Botpress
                    │
           Phase 20 Testing Hardening
                    │
           Phase 21 Deployment & Production Readiness
```

Note: Phase 8 (RAG) has no dependency on Phases 4–7 and could technically be built any time after Phase 2; it is sequenced where shown because Phase 9 (Agents) is its only consumer and this keeps the roadmap linear for a solo developer. See "Parallel Development Opportunities" below if you want to build it earlier.

## 2. Critical Path

Phase 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 9 → 10 → 11 → 12 → 13 → 14 → 16 → 18 → 19 → 20 → 21

This is the longest true dependency chain and determines the minimum project timeline (Phase 8 and Phase 15 sit off the critical path but must complete before Phase 9 and Phase 17/19 respectively). Phase 17 depends on 3/4/12/15 but not on 6/7/9/10, so it can start as soon as those four are done — see below.

## 3. Parallel Development Opportunities

Even for a solo developer, these pairings can be interleaved (worked on in alternating sessions) rather than strictly serialized, since they don't share write-paths:

- **Phase 8 (RAG)** can be built any time after Phase 2, in parallel with Phases 4–7 (different data, different tables, no shared services).
- **Phase 17 (Frontend Foundation)** can start as soon as Phases 3, 4, 12, and 15 are done — it does not need Phases 5–11 or 13–14 to exist, since Dashboard only needs auth/market-data/portfolio/notifications.
- **Phase 15 (Notifications)** can be scaffolded (schema + service shell) as early as Phase 11, and only needs full event-source wiring once Phase 14 completes.
- **Frontend component library / design-system work** (not a phase itself) can happen anytime after Phase 0, ahead of when it's needed.

True parallelism (multiple people) would additionally allow Phase 6 (Forecasting) and Phase 8 (RAG) to be built by different contributors simultaneously once Phase 2 is done.

## 4. Major Project Risks

- **Model-serving complexity for TimesFM/Chronos/PatchTST/FinRL**: these are heavier than XGBoost/LightGBM and may require GPU or specialized runtime; underestimating this could stall Phase 6 extensions. Mitigate by shipping Phase 6 with tree-based models first (as planned) and treating the deep forecasting models as a post-Phase-21 enhancement track.
- **Broker sandbox limitations (Upstox/Zerodha)**: sandbox environments may not fully replicate production behavior (fills, latency, rejections), risking under-tested live-trading paths. Mitigate with extensive paper-trading coverage and conservative initial risk-profile defaults.
- **RAG data-source licensing**: some knowledge sources (analyst reports, certain news feeds) require licensing; scope Phase 8 to freely available sources first (public news, filings, Wikipedia) and treat licensed sources as a future enhancement.
- **LangGraph/multi-agent orchestration complexity**: Phase 9 is the largest phase; underestimating agent-interdependency debugging time is the single biggest schedule risk. Mitigate by building/testing agents individually before wiring the full graph.
- **Circular dependency between Portfolio Engine and Broker Layer**: addressed architecturally in this roadmap (Phase 12 builds paper-trading portfolio logic behind the same interface Phase 14 extends for live sync) — but requires discipline to keep that interface stable across both phases.
- **Solo-developer time risk on Phase 18 (frontend feature modules)** and **Phase 9 (agents)**: these are the two highest-effort phases; consider splitting each into two working sub-milestones internally even though they are tracked as single phases here.
- **Secrets/credential handling for four external integrations** (Upstox, Zerodha, LLM provider, Qdrant): a single mishandled `.env` commit is a real risk; enforce the CI secret-scanning step from Phase 21 starting in Phase 0, not just at the end.



## 5. Suggested Git Branch Strategy

- `main` — always deployable; protected; merges only via reviewed PRs with passing CI.
- `develop` (optional for solo dev; skip if you prefer trunk-based development directly against feature branches merging to `main`).
- `feature/<phase-name>` per phase or sub-deliverable, e.g. `feature/market-data`, `feature/forecasting`, `feature/agents`, `feature/upstox`, `feature/rag`, matching the naming examples in §8.
- `bugfix/<short-description>` for post-merge fixes, e.g. `bugfix/news-parser`.
- `refactor/<area>` for non-behavioral changes, e.g. `refactor/database`.
- `docs/<topic>` for documentation-only changes.
- Tag production releases as `v0.<phase-number>.0` at the end of each phase that lands on `main` (see Milestone Release Plan).



## 6. Recommended Commit Strategy

- Follow Conventional Commits throughout (per §7/§8): `feat:`, `fix:`, `refactor:`, `docs:`, `test:`.
- Keep commits atomic and scoped to one logical change; avoid bundling unrelated services in one commit.
- Every commit that touches business logic should be accompanied by its tests in the same commit, not a follow-up one.
- Squash-merge feature branches into `main` so `main`'s history reads as one commit per completed unit of work.
- Never commit `.env`, credentials, generated build artifacts, or commented-out legacy code (per §7 Prohibited Practices).



## 7. Milestone Release Plan


| Milestone                           | Phases Included | What Ships                                                     |
| ----------------------------------- | --------------- | -------------------------------------------------------------- |
| **v0.1 — Foundation**               | 0–3             | Running skeleton with auth and API versioning.                 |
| **v0.2 — Market Intelligence**      | 4–7             | Real market data, features, forecasting, ensemble predictions. |
| **v0.3 — Knowledge & Reasoning**    | 8–10            | RAG-grounded, multi-agent, explainable recommendations.        |
| **v0.4 — Trading Core**             | 11–14           | Risk-validated paper and live trading through Upstox/Zerodha.  |
| **v0.5 — Learning & Notifications** | 15–16           | Notification delivery and RLAIF-driven performance tracking.   |
| **v0.6 — Full Product Experience**  | 17–19           | Complete frontend and Botpress conversational assistant.       |
| **v1.0 — Production Release**       | 20–21           | Fully tested, hardened, deployed production system.            |


Each milestone corresponds to a tagged, deployable state of `main` and a good natural point for a portfolio demo or internship-application showcase, since v0.2 onward already demonstrates real, working AI/ML functionality end-to-end.

## 8. Definition of Done (applies to every phase)

A phase is **not** complete until all of the following are true:

- [ ] All deliverables listed in the phase are implemented and merged to `main`.
- [ ] All new services/interfaces follow Clean Architecture, SOLID, and dependency-injection conventions from §7.
- [ ] All new database tables have migrations that apply and roll back cleanly.
- [ ] All new API endpoints are documented in OpenAPI/Swagger and follow the standardized request/response envelope.
- [ ] Unit tests exist for all new business logic; integration tests exist for all new cross-service interactions; the phase's stated testing requirements are met.
- [ ] No secrets, credentials, or environment-specific values are committed to source control.
- [ ] No prototype/placeholder code, duplicate logic, or commented-out legacy code remains in the merged result.
- [ ] The application starts successfully via `docker compose up` and passes its health check.
- [ ] The phase's own completion checklist (above) is fully checked off.
- [ ] The phase introduces no circular dependency on any later phase.