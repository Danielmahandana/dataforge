.PHONY: help up down restart logs backend-dev frontend-dev install test test-backend test-frontend build

help:
	@echo "Darkroom DataForge — Management Commands"
	@echo "  make up            - Start all services with Docker Compose"
	@echo "  make down          - Stop all Docker Compose services"
	@echo "  make restart       - Restart all Docker Compose services"
	@echo "  make logs          - Tail logs from all containers"
	@echo "  make backend-dev   - Run backend locally with uvicorn"
	@echo "  make frontend-dev  - Run frontend locally with vite"
	@echo "  make test          - Run both backend and frontend tests"
	@echo "  make build         - Build frontend for production"

up:
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose down && docker compose up -d

logs:
	docker compose logs -f

backend-dev:
	uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

frontend-dev:
	cd frontend && npm run dev

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

test: test-backend test-frontend

test-backend:
	pytest tests/test_api_v1.py tests/test_pipeline_e2e.py -v

test-frontend:
	cd frontend && npm run build

build:
	cd frontend && npm run build
