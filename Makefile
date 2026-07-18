.PHONY: help start start-sqlite start-smoke dev test lint typecheck build clean install docker-up docker-down docker-logs docker-build docker-ps docker-health db-migrate db-downgrade db-revision validate validate-api validate-web demo-seed demo-reset demo-smoke release-check release-evidence

# Default target
.DEFAULT_GOAL := help

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)CampusAgent Development Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)⚠️  重要提示：所有后端命令必须在 CampusAgent Conda 环境中运行$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "$(YELLOW)Usage:$(NC) make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

start: ## One-click start (auto Docker if available, SQLite fallback otherwise)
	@./scripts/start.sh

start-sqlite: ## One-click start using SQLite fallback
	@./scripts/start.sh --mode sqlite

start-smoke: ## Run one-click smoke verification and exit
	@./scripts/start.sh --smoke

# Development
dev: ## Start all development services
	@echo "$(GREEN)Starting development services...$(NC)"
	@echo "$(YELLOW)Note: Docker is required for full environment$(NC)"
	@echo "Starting Next.js dev server..."
	@cd apps/web && pnpm dev &
	@echo "Starting FastAPI dev server..."
	@cd apps/api && conda run -n CampusAgent uvicorn src.main:app --reload --port 8000 &
	@echo "$(GREEN)Development servers started$(NC)"
	@echo "  - Web: http://localhost:3000"
	@echo "  - API: http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"

# Testing
test: ## Run all tests
	@echo "$(GREEN)Running all tests...$(NC)"
	@cd apps/web && pnpm test
	@cd apps/api && conda run -n CampusAgent pytest

test-watch: ## Run tests in watch mode
	@echo "$(GREEN)Running tests in watch mode...$(NC)"
	@cd apps/web && pnpm test:watch
	@cd apps/api && conda run -n CampusAgent pytest -v --tb=short

# Code quality
lint: ## Run linting
	@echo "$(GREEN)Running linters...$(NC)"
	@echo "Frontend (ESLint)..."
	@cd apps/web && pnpm lint
	@echo "Backend (Ruff)..."
	@cd apps/api && conda run -n CampusAgent ruff check .

typecheck: ## Run type checking
	@echo "$(GREEN)Running type checks...$(NC)"
	@echo "Frontend (TypeScript)..."
	@cd apps/web && pnpm typecheck
	@echo "Backend (mypy)..."
	@cd apps/api && conda run -n CampusAgent mypy .

# Build
build: ## Build all applications
	@echo "$(GREEN)Building all applications...$(NC)"
	@cd apps/web && pnpm build
	@echo "$(GREEN)Build complete$(NC)"

# Cleanup
clean: ## Clean build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	@cd apps/web && rm -rf .next out node_modules/.cache
	@cd apps/api && find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)Clean complete$(NC)"

# Installation
install: ## Install all dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	@corepack pnpm install --frozen-lockfile
	@conda run -n CampusAgent python -m pip install -r apps/api/requirements.lock
	@echo "$(GREEN)Installation complete$(NC)"

# Setup (first time)
setup: install ## Initial project setup
	@echo "$(GREEN)Running initial setup...$(NC)"
	@echo "$(YELLOW)Don't forget to:$(NC)"
	@echo "  1. Copy .env.example to .env and configure"
	@echo "  2. Start Docker services: make docker-up"
	@echo "  3. Run database migrations"
	@echo "$(GREEN)Setup complete!$(NC)"

# Docker (requires Docker installed)
docker-up: ## Start core Docker services (postgres, redis, mock-model)
	@echo "$(GREEN)Starting core Docker services...$(NC)"
	docker compose up -d postgres redis mock-model
	@echo "$(GREEN)Core services started$(NC)"
	@echo "  - PostgreSQL: http://localhost:5432"
	@echo "  - Redis:      http://localhost:6379"
	@echo "  - Mock Model: http://localhost:8001"

docker-up-all: ## Start ALL Docker services (web, api, postgres, redis, mock-model)
	@echo "$(GREEN)Starting all Docker services...$(NC)"
	docker compose up -d
	@echo "$(GREEN)All services started$(NC)"
	@echo "  - Web:        http://localhost:3000"
	@echo "  - API:        http://localhost:8000"
	@echo "  - PostgreSQL: http://localhost:5432"
	@echo "  - Redis:      http://localhost:6379"
	@echo "  - Mock Model: http://localhost:8001"

docker-down: ## Stop all Docker services
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	docker compose down
	@echo "$(GREEN)Docker services stopped$(NC)"

docker-logs: ## Show Docker logs (follow mode)
	docker compose logs -f

docker-build: ## Build all Docker images
	@echo "$(GREEN)Building Docker images...$(NC)"
	docker compose build
	@echo "$(GREEN)Build complete$(NC)"

docker-ps: ## Show running Docker containers
	docker compose ps

docker-health: ## Check health of all Docker services
	@echo "$(GREEN)Checking service health...$(NC)"
	docker compose ps --format "table {{.Name}}\t{{.Status}}"

# Database
db-migrate: ## Run database migrations (upgrade head)
	@echo "$(GREEN)Running migrations...$(NC)"
	@cd apps/api && conda run -n CampusAgent alembic -c alembic.ini upgrade head
	@echo "$(GREEN)Migrations complete$(NC)"

db-downgrade: ## Downgrade database to base
	@echo "$(YELLOW)Downgrading database to base...$(NC)"
	@cd apps/api && conda run -n CampusAgent alembic -c alembic.ini downgrade base
	@echo "$(GREEN)Downgrade complete$(NC)"

db-revision: ## Create a new migration revision (usage: make db-revision m="description")
	@echo "$(GREEN)Creating new migration...$(NC)"
	@cd apps/api && conda run -n CampusAgent alembic -c alembic.ini revision -m "$(m)"
	@echo "$(GREEN)Migration created$(NC)"

# Code formatting
format: ## Format all code
	@echo "$(GREEN)Formatting code...$(NC)"
	@cd apps/web && pnpm exec prettier --write .
	@cd apps/api && conda run -n CampusAgent ruff format .
	@echo "$(GREEN)Formatting complete$(NC)"

# ----------------------------------------------------------------
# P13 Release Candidate targets
# ----------------------------------------------------------------

# Validation — run quality gates for API and Web separately.
validate: validate-api validate-web ## Run all validation (API + Web)
	@echo "$(GREEN)All validation passed.$(NC)"

validate-api: ## Validate API: ruff + mypy + pytest (no Docker required)
	@echo "$(BLUE)Validating API...$(NC)"
	cd apps/api && conda run -n CampusAgent ruff check . --no-cache
	cd apps/api && conda run -n CampusAgent mypy src tests --no-incremental
	cd apps/api && conda run -n CampusAgent python -m pytest tests -q -p no:cacheprovider
	@echo "$(GREEN)API validation passed.$(NC)"

validate-web: ## Validate Web: lint + typecheck + test + build (no Docker required)
	@echo "$(BLUE)Validating Web...$(NC)"
	corepack pnpm lint
	corepack pnpm typecheck
	corepack pnpm test
	corepack pnpm --filter @campus-agent/web build
	@echo "$(GREEN)Web validation passed.$(NC)"

# Demo data — seed / reset / smoke (no Docker required, uses SQLite in-memory).
demo-reset: ## Reset demo data (deletes demo namespace only, fail-closed in production)
	@echo "$(YELLOW)Resetting demo data...$(NC)"
	conda run -n CampusAgent python scripts/demo/reset_demo.py
	@echo "$(GREEN)Demo data reset complete.$(NC)"

demo-seed: ## Seed demo data (idempotent, safe to re-run)
	@echo "$(GREEN)Seeding demo data...$(NC)"
	conda run -n CampusAgent python scripts/demo/seed_demo.py
	@echo "$(GREEN)Demo data seeded.$(NC)"

demo-smoke: ## Run in-process demo smoke test (11 steps, no Docker/server required)
	@echo "$(BLUE)Running demo smoke test...$(NC)"
	conda run -n CampusAgent python scripts/demo/run_demo_smoke.py
	@echo "$(GREEN)Demo smoke test passed.$(NC)"

# Release candidate checks.
release-check: ## Check release candidate readiness (docs, secrets, contracts)
	@echo "$(BLUE)Running release candidate checks...$(NC)"
	conda run -n CampusAgent python scripts/release/check_release_candidate.py
	@echo "$(GREEN)Release candidate checks passed.$(NC)"

release-evidence: ## Collect release evidence (git, pytest, pnpm, pip summaries)
	@echo "$(BLUE)Collecting release evidence...$(NC)"
	conda run -n CampusAgent python scripts/release/collect_evidence.py
	@echo "$(GREEN)Release evidence collected.$(NC)"
