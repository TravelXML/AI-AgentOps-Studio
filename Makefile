.PHONY: install dev dev-api dev-web test test-api test-web test-e2e lint lint-api lint-web \
        format migrate migrate-new seed down build up logs clean

install: ## Install all Python and Node dependencies
	uv sync --all-packages
	cd apps/web && npm install
	cd tests/e2e && npm install

dev: ## Start Postgres + Redis, then run the API and web dev servers (Ctrl+C stops both)
	docker compose up -d postgres redis
	$(MAKE) -j2 dev-api dev-web

dev-api: ## Run the FastAPI dev server (expects Postgres/Redis already up)
	cd apps/api && uv run --project .. alembic upgrade head
	uv run --all-packages uvicorn agentq_api.main:app --reload --host 0.0.0.0 --port 8000

dev-web: ## Run the Next.js dev server
	cd apps/web && npm run dev

test: test-api test-web ## Run the full backend + frontend test suites

test-api: ## Run backend unit + integration tests (pytest)
	uv run --all-packages pytest

test-web: ## Typecheck, lint, and unit-test the frontend
	cd apps/web && npm run typecheck && npm run lint

test-e2e: ## Run Playwright E2E tests against already-running dev servers
	cd tests/e2e && npx playwright test

lint: lint-api lint-web ## Lint everything

lint-api: ## Ruff lint + format check for all Python packages
	uv run --all-packages ruff check .
	uv run --all-packages ruff format --check .

lint-web: ## ESLint + tsc for the frontend
	cd apps/web && npm run lint && npm run typecheck

format: ## Auto-format Python and frontend code
	uv run --all-packages ruff format .
	uv run --all-packages ruff check . --fix
	cd apps/web && npm run lint -- --fix

migrate: ## Apply database migrations
	cd apps/api && uv run --project .. alembic upgrade head

migrate-new: ## Generate a new Alembic migration from model changes (usage: make migrate-new msg="add x")
	cd apps/api && uv run --project .. alembic revision --autogenerate -m "$(msg)"

seed: ## Load example flows into the local database
	uv run --all-packages python infrastructure/scripts/seed_examples.py

build: ## Build all Docker images
	docker compose build

up: ## Start the full stack (Postgres, Redis, API, web) via Docker Compose
	docker compose up -d
	@echo "Web:    http://localhost:3000"
	@echo "API:    http://localhost:8000"
	@echo "Docs:   http://localhost:8000/docs"

logs: ## Tail logs from all Docker Compose services
	docker compose logs -f

down: ## Stop and remove all Docker Compose services
	docker compose down

clean: ## Stop services and remove volumes (DESTROYS local database data)
	docker compose down -v
