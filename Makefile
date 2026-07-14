.PHONY: help dev test lint typecheck build clean install

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
	@pnpm install
	@echo "$(GREEN)Installation complete$(NC)"

# Setup (first time)
setup: install ## Initial project setup
	@echo "$(GREEN)Running initial setup...$(NC)"
	@echo "$(YELLOW)Don't forget to:$(NC)"
	@echo "  1. Copy .env.example to .env and configure"
	@echo "  2. Start Docker services: make docker-up"
	@echo "  3. Run database migrations"
	@echo "$(GREEN)Setup complete!$(NC)"

# Docker (when Docker is available)
docker-up: ## Start Docker services (PostgreSQL, Redis)
	@echo "$(GREEN)Starting Docker services...$(NC)"
	@docker compose up -d postgres redis
	@echo "$(GREEN)Docker services started$(NC)"

docker-down: ## Stop Docker services
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	@docker compose down
	@echo "$(GREEN)Docker services stopped$(NC)"

docker-logs: ## Show Docker logs
	@docker compose logs -f

# Database
db-migrate: ## Run database migrations
	@echo "$(GREEN)Running migrations...$(NC)"
	@cd apps/api && conda run -n CampusAgent alembic upgrade head
	@echo "$(GREEN)Migrations complete$(NC)"

# Code formatting
format: ## Format all code
	@echo "$(GREEN)Formatting code...$(NC)"
	@cd apps/web && pnpm exec prettier --write .
	@cd apps/api && conda run -n CampusAgent ruff format .
	@echo "$(GREEN)Formatting complete$(NC)"
