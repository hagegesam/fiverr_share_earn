# Fiverr Shareable Links API

A FastAPI backend service that powers short, trackable URLs for Fiverr sellers. Sellers generate short links, share them externally, and earn **$0.05 in Fiverr credits** per valid click.

---

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 14+ (or Docker)

### Option A — Local

```bash
# 1. Clone and enter the project
cd fiverr-shortlinks

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your Postgres credentials:
#   DATABASE_URL=postgresql://user:password@localhost:5432/fiverr_shortlinks

# 5. Create the database
createdb fiverr_shortlinks

# 6. Start the server (tables are created automatically on startup)
uvicorn app.main:app --reload
```

### Option B — Docker

```bash
docker compose up --build
```

This starts both Postgres and the API. The app waits for the database health check before booting.

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:password@localhost:5432/fiverr_shortlinks` |

The app loads `.env` automatically via `python-dotenv`. When running with Docker Compose the variable is injected through the compose file.

Once running, the API is available at `http://localhost:8000` with interactive docs at `/docs` (Swagger) and `/redoc`.

---

## Architecture

### Project Structure

```
fiverr-shortlinks/
├── app/
│   ├── main.py        ← FastAPI app + all 3 endpoints
│   ├── database.py    ← Engine, session factory, get_db dependency
│   ├── models.py      ← SQLAlchemy models (Link, Click)
│   ├── schemas.py     ← Pydantic request/response validation
│   ├── services.py    ← Business logic (create, record, stats)
│   └── utils.py       ← Short code generator + fraud simulation
├── tests/
│   ├── conftest.py    ← Test fixtures (in-memory SQLite)
│   └── test_api.py    ← 16 test cases for all endpoints
├── docker-compose.yml ← Postgres + app containers
├── Dockerfile         ← Python 3.12 slim image
├── requirements.txt   ← Pinned dependencies
├── .env.example       ← Environment variable template
├── DESIGN.md          ← Full design specification
└── README.md          ← This file
```

**Why flat?** — The scope is three endpoints and two tables. A flat layout keeps navigation simple and avoids premature abstraction.

### Component Interaction

```
Client Request
      │
      ▼
  main.py          ← Routes: POST /links, GET /{code}, GET /stats
      │
      ▼
  schemas.py       ← Validates request body / query params
      │
      ▼
  services.py      ← Business logic (create_link, record_click, get_stats)
      │
      ├──► utils.py       ← generate_short_code(), simulate_fraud_check()
      │
      ▼
  models.py        ← ORM: Link, Click
      │
      ▼
  database.py      ← SQLAlchemy engine + session → PostgreSQL
```

### Request Flows

**POST /links** — `main.py` validates the body with `LinkCreate` schema, calls `services.create_link()` which checks for duplicates then generates a short code with collision retry. Returns 201 (new) or 200 (existing).

**GET /{short_code}** — `main.py` calls `services.get_link_by_short_code()`, runs the async fraud check from `utils.py` (100ms simulation), calls `services.record_click()`, returns 302 redirect.

**GET /stats** — `main.py` passes validated pagination params to `services.get_stats()` which queries links with click counts, computes earnings ($0.05 x clicks), and groups clicks by month.

### Database Schema

Two tables with a one-to-many relationship:

```
links                          clicks
┌──────────────┐               ┌──────────────┐
│ id (UUID PK) │──────────────<│ id (UUID PK) │
│ short_code   │   1       N   │ link_id (FK)  │
│ target_url   │               │ clicked_at    │
│ created_at   │               └──────────────┘
└──────────────┘
```

Indexes: `links.short_code` (unique), `clicks.link_id` (for aggregation).

---

## Testing

Tests use an **in-memory SQLite** database so no PostgreSQL is needed to run them.

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Single test class
pytest tests/test_api.py::TestPostLinks -v

# With coverage (install pytest-cov first)
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

### Test Coverage

| Endpoint | Cases | What's tested |
|---|---|---|
| **POST /links** | 6 | Create link, duplicate returns 200, different URLs get different codes, missing/empty/invalid URL |
| **GET /{code}** | 4 | 302 redirect, 404 not found, click recorded in stats, multiple clicks tracked |
| **GET /stats** | 6 | Empty response, links listed, pagination across pages, limit/page validation, earnings math, monthly breakdown |

### Manual Testing

With the server running:

```bash
# Create a link
curl -X POST http://localhost:8000/links \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://fiverr.com/john/logo-design"}'

# Follow a short link (use -v to see the 302)
curl -v http://localhost:8000/<short_code>

# View stats
curl http://localhost:8000/stats?page=1&limit=10
```

---

## AI Environment Setup

This project was built using **Claude Code** (Anthropic's CLI agent). Below is the setup used to maintain quality and consistency across prompts.

### Prompt Sequence

The implementation followed a strict 11-step prompt sequence defined in [DESIGN.md](DESIGN.md) (see "Claude Code Prompts Sequence" section). Each prompt targets a single file, keeping changes focused and reviewable.

### Design-First Approach

[DESIGN.md](DESIGN.md) was written before any code. It serves as the single source of truth for:
- Database schema and constraints
- API contracts with exact JSON shapes
- Project structure and file responsibilities
- Design decisions with rationale

This gives the AI agent full context in a single file read, reducing hallucination and keeping all generated code aligned with the spec.

### Recommended Rules for AI-Assisted Development

If using Claude Code, create a `CLAUDE.md` in the project root with rules like:

```markdown
# CLAUDE.md

## Project context
- Read DESIGN.md before making changes
- This is a FastAPI + SQLAlchemy + PostgreSQL project
- Flat structure: all app code lives directly in app/

## Code style
- Use Pydantic v2 conventions (model_config, field_validator)
- Use timezone-aware datetimes (datetime.now(timezone.utc))
- Keep services.py as the single business logic layer

## Testing
- Tests use in-memory SQLite (see tests/conftest.py)
- Run pytest before marking any task complete

## Constraints
- Do not add sub-packages (routes/, services/, utils/)
- Do not add dependencies without asking
- Do not create migration files — tables auto-create on startup
```

### Useful Plugins and Tools

| Tool | Purpose |
|---|---|
| **Claude Code CLI** | AI-powered development agent |
| **FastAPI /docs** | Built-in Swagger UI for manual testing |
| **Docker Compose** | One-command Postgres + app setup |
| **pytest + httpx** | Automated testing with FastAPI TestClient |
| **python-dotenv** | Environment variable management |

### Improvements Made Beyond Base Spec

- **Timezone-aware timestamps**: Uses `datetime.now(timezone.utc)` instead of deprecated `utcnow()`
- **Pydantic v2 style**: `model_config`, `field_validator` with `@classmethod`
- **Proper status codes**: 201 for new links, 200 for duplicates (not just 201 for both)
- **Docker healthcheck**: App waits for Postgres readiness before starting
- **SQLite `to_char` shim**: Custom function in test conftest so services.py works unchanged in tests
