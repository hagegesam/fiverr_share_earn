# Fiverr Shareable Links — Design Document

## Project Overview

Build a backend service that powers short, trackable URLs for Fiverr sellers. Sellers generate short links, share them externally, and earn $0.05 in Fiverr credits per valid click.

---

## Tech Stack

- **Language**: Python 3.x
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Short code format | 6 chars, alphanumeric (a-z, 0-9), lowercase | Simple, readable, ~2 billion combinations |
| Short code generation | Random with collision check | Simple to implement |
| Duplicate URL handling | Globally unique — return existing link if same URL requested | Per requirement |
| Fraud validation | Simulated 100ms delay, always passes | Per requirement (simulation) |
| Click storage | Individual rows with timestamp | Enables monthly breakdown analytics |
| Monthly breakdown | Grouped by click date | Business-relevant metric |
| Pagination | Offset-based, default 20 per page | Simple, sufficient for this scope |
| Earnings calculation | `total_clicks × $0.05`, computed on the fly | No separate credits table needed |

---

## Database Schema

### Table: `links`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PRIMARY KEY |
| `short_code` | VARCHAR(6) | UNIQUE, INDEXED |
| `target_url` | TEXT | UNIQUE |
| `created_at` | TIMESTAMP | DEFAULT NOW() |

### Table: `clicks`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PRIMARY KEY |
| `link_id` | UUID | FOREIGN KEY → links.id |
| `clicked_at` | TIMESTAMP | DEFAULT NOW() |

**Index**: `clicks.link_id` for fast aggregation queries.

---

## API Contracts

### 1. POST /links — Generate Short Link

**Request:**
```json
{
  "target_url": "https://fiverr.com/john/logo-design"
}
```

**Response (201 Created or 200 if exists):**
```json
{
  "short_code": "xk9mt2",
  "short_url": "http://localhost:8000/xk9mt2",
  "target_url": "https://fiverr.com/john/logo-design",
  "created_at": "2025-02-11T10:30:00Z"
}
```

**Edge cases:**
- Missing/empty `target_url` → 400 Bad Request
- Invalid URL format → 400 Bad Request

---

### 2. GET /{short_code} — Redirect and Track

**Flow:**
1. Look up `short_code` in database
2. If not found → 404 Not Found
3. Run fraud validation (simulate 100ms delay)
4. If passed → record click in `clicks` table
5. Return 302 Redirect to `target_url`

**Response:** HTTP 302 with `Location` header

---

### 3. GET /stats — Global Analytics

**Request:** `GET /stats?page=1&limit=20`

**Response:**
```json
{
  "page": 1,
  "limit": 20,
  "total_links": 54,
  "links": [
    {
      "short_code": "xk9mt2",
      "target_url": "https://fiverr.com/john/logo-design",
      "total_clicks": 150,
      "total_earnings": 7.50,
      "monthly_breakdown": [
        { "month": "2025-01", "clicks": 80 },
        { "month": "2025-02", "clicks": 70 }
      ]
    }
  ]
}
```

**Edge cases:**
- `page` < 1 → default to 1
- `limit` > 100 → cap at 100

---

## Project Structure

```
fiverr-shortlinks/
├── app/
│   ├── main.py           # FastAPI app + all 3 endpoints
│   ├── models.py         # SQLAlchemy models (Link, Click)
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── database.py       # Engine, session, config
│   ├── services.py       # All business logic (link creation, click recording, stats)
│   └── utils.py          # Short code generation + fraud simulation
├── tests/
│   └── test_api.py       # All endpoint tests
├── docker-compose.yml    # Postgres container setup
├── Dockerfile            # App container
├── .env.example          # Environment variables template
├── requirements.txt
├── README.md
├── MANIFEST.mf
└── DESIGN.md (this file)
```

**Why this structure:**
- Flat and simple — appropriate for project scope and 90-minute time limit
- Easy for reviewers to navigate
- Docker included — shows deployment awareness

---

## Implementation Order

1. **Setup**: Project scaffold, database connection, models
2. **POST /links**: Short code generation, duplicate handling
3. **GET /{short_code}**: Redirect with fraud check and click recording
4. **GET /stats**: Pagination, aggregation, monthly breakdown
5. **Tests**: Automated test suite
6. **Documentation**: README.md and MANIFEST.mf

---

## Claude Code Prompts Sequence

Use these prompts in order:

1. "Read DESIGN.md. Set up the FastAPI project with the folder structure defined there. Include requirements.txt with FastAPI, SQLAlchemy, psycopg2-binary, uvicorn, pytest, and python-dotenv."

2. "Create database.py with SQLAlchemy engine and session. Use environment variables for the connection string with python-dotenv."

3. "Create the SQLAlchemy models in models.py for Link and Click as defined in DESIGN.md."

4. "Create the Pydantic schemas in schemas.py for request/response validation."

5. "Create utils.py with the short code generator (6 chars, alphanumeric) and the fraud check simulator (100ms delay, always returns True)."

6. "Create services.py with business logic: create_link (handles duplicates), record_click, and get_stats (with pagination and monthly breakdown)."

7. "Create main.py with all three endpoints (POST /links, GET /{short_code}, GET /stats) using the services."

8. "Create docker-compose.yml for Postgres and Dockerfile for the FastAPI app."

9. "Create .env.example with required environment variables."

10. "Write test_api.py with automated tests for all three endpoints. Use pytest and FastAPI TestClient."

11. "Generate README.md with setup instructions (local and Docker) and MANIFEST.mf template."
