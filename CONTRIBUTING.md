# Contributing to AgentQ

## Setup

```bash
cp .env.example .env
docker compose up -d postgres redis
make install
make migrate
make dev-api   # in one terminal
make dev-web   # in another
```

## Before opening a PR

```bash
make lint
make test
make test-e2e   # needs dev-api + dev-web running
```

- No `# noqa`, `eslint-disable`, or `type: ignore` as a shortcut for a real fix - see
  `promots.md` section 59.
- New database schema changes go through Alembic (`make migrate-new msg="..."`), never
  `Base.metadata.create_all()`.
- New node types: see `docs/development/creating-node.md`.
- New built-in tools: see `docs/development/creating-tool.md`.
- Keep FlowSpec framework-neutral - the UI and the database must never see LangGraph internals
  directly; go through the compiler.

## Commit style

Small, logical commits. Describe *why*, not just *what* - the diff already shows what changed.

## Code of conduct

Be respectful, be specific, assume good faith.
