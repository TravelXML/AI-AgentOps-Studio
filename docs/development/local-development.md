# Local Development

## Fastest path (Docker for everything)

```bash
cp .env.example .env
docker compose up -d
make seed   # optional: loads examples/ into the UI
```

Web: http://localhost:3000 · API: http://localhost:8000 · API docs: http://localhost:8000/docs

## Fastest path for iterating on code (hybrid)

Run Postgres/Redis in Docker, API and web natively (hot reload, faster iteration):

```bash
docker compose up -d postgres redis
make install
make migrate
make dev-api    # terminal 1 - uvicorn --reload on :8000
make dev-web    # terminal 2 - next dev on :3000
```

## Make targets

Run `make help`-style by reading the `Makefile` directly - every target has a one-line comment.
The ones you'll use most: `install`, `dev`, `test`, `test-e2e`, `lint`, `format`, `migrate`,
`migrate-new msg="..."`, `seed`, `up`, `down`, `logs`.

## Database migrations

Every schema change goes through Alembic - never `Base.metadata.create_all()` in production code
paths (tests use `create_all` against a throwaway test database for speed; that's a deliberate,
documented exception, not the migration strategy).

```bash
# after editing apps/api/src/agentq_api/db/models.py
make migrate-new msg="add knowledge_bases table"
make migrate
```

## Running tests

```bash
make test         # pytest (backend) - needs a Postgres reachable at DATABASE_URL / a test DB
make test-e2e      # Playwright - needs API (:8000) and web (:3000) already running
```

The backend test suite creates/drops its schema against `agentq_test` (a separate database
from your dev `agentq` database) on every run via `apps/api/tests/conftest.py` - it will not
touch your dev data.

## Common gotchas

- **uv workspace + a package with no files yet**: if you add a new package directory before it
  has any Python files, `uv sync` may cache an empty wheel for it. Fix: `uv sync --all-packages
  --reinstall-package <name>` after adding real source files.
- **CORS + custom response headers**: any new custom response header the frontend needs to read
  (like `X-Run-Id`) must be added to `expose_headers` in `apps/api/src/agentq_api/main.py`'s
  `CORSMiddleware` config, or `response.headers.get(...)` will silently return `null` in the
  browser even though the header is present on the wire. This bit us once - see the E2E test
  history for how it was caught.
- **LangGraph checkpointer tables**: `checkpoint*` tables are created by
  `AsyncPostgresSaver.setup()`, not Alembic. `apps/api/alembic/env.py` has an `include_name` filter
  so `alembic revision --autogenerate` never tries to drop them.
