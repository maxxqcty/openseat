PYTHON ?= python

BACKEND := backend
FRONTEND := frontend

.PHONY: install dev test e2e lint fmt seed seed-reset docker-up docker-down docker-build render-validate render-verify

install:
	cd $(BACKEND) && uv sync
	cd $(FRONTEND) && npm ci

dev:
	$(PYTHON) scripts/dev.py

test:
	cd $(BACKEND) && uv run pytest
	cd $(FRONTEND) && npm run test

e2e:
	$(PYTHON) scripts/e2e.py

lint:
	cd $(BACKEND) && uv run ruff check .
	cd $(BACKEND) && uv run mypy app
	cd $(FRONTEND) && npm run lint
	cd $(FRONTEND) && npm run typecheck

seed:
	cd $(BACKEND) && uv run python -m app.seed

seed-reset:
	cd $(BACKEND) && uv run python -m app.seed --reset

fmt:
	cd $(BACKEND) && uv run ruff check --fix .
	cd $(BACKEND) && uv run ruff format .
	cd $(FRONTEND) && npm run format

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-down-v:
	docker compose down -v

# Render (issue #15): render.yaml at the repo root creates the free web
# service and Postgres database. Merging to main deploys; roll back from the
# Render dashboard.

render-validate:
	$(PYTHON) scripts/render.py validate

render-verify:
	$(PYTHON) scripts/render.py verify $(URL)
