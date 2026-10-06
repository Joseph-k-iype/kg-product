SHELL := /bin/bash
PY := backend/.venv/bin/python
PLAN_WORKSPACE := .superpowers/sdd/2026-10-06-knowledge-product-manager
.PHONY: install services up migrate model seed dev api worker test test-fast test-integration test-e2e check-ui build reset docs docs-check
install:
	uv sync --project backend --python 3.12 --extra test --extra embeddings
	npm ci --prefix frontend
services:
	docker compose up -d postgres minio falkordb
up:
	docker compose up -d --build
migrate:
	cd backend && .venv/bin/alembic upgrade head
model:
	cd backend && PYTHONPATH=. .venv/bin/python ../scripts/download_model.py
seed:
	cd backend && PYTHONPATH=. .venv/bin/python ../scripts/seed.py
api:
	cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 58000
worker:
	cd backend && .venv/bin/python -m app.worker
dev:
	npm run dev --prefix frontend -- --port 5174 --strictPort
test:
	cd backend && PYTHONPATH=. .venv/bin/python ../scripts/prepare_test_db.py
	cd backend && DATABASE_URL=postgresql+psycopg://knowledge:knowledge-local@localhost:55432/knowledge_test .venv/bin/alembic upgrade head
	cd backend && .venv/bin/python -m pytest -q
test-fast:
	cd backend && .venv/bin/python -m pytest -q -m 'not model'
test-integration: test
check-ui:
	npm run check --prefix frontend
test-e2e:
	cd frontend && npx playwright install chromium && npx playwright test
build:
	npm run build --prefix frontend
docs:
	cd backend && PYTHONPATH=. .venv/bin/python ../scripts/export_reference.py
docs-check:
	cd backend && PYTHONPATH=. .venv/bin/python ../scripts/export_reference.py --check
reset:
	cd backend && PYTHONPATH=. .venv/bin/python ../scripts/reset.py --confirm-reset
