PYTHON ?= python

BACKEND := backend
FRONTEND := frontend

.PHONY: install dev test e2e lint fmt seed seed-reset docker-up docker-down docker-build render-validate render-verify render-deploy-hook render-promote render-rollback on-call audit

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
	cd $(BACKEND) && uv run ruff check ../on-call ../scripts
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
	cd $(BACKEND) && uv run python ../scripts/render.py validate

render-verify:
	cd $(BACKEND) && uv run python ../scripts/render.py verify $(URL)

# The deploy hook is the guarded fallback when Render cannot read GitHub
# checks. The workflow calls it after E2E; use it locally only for a dry run.
render-deploy-hook:
	cd $(BACKEND) && uv run python ../scripts/render.py deploy-hook $(ARGS)

# Paid image-backed promotion and rollback. The free demo uses the Render
# dashboard. Both commands require the production GitHub Environment in CI.
render-promote:
	cd $(BACKEND) && uv run python ../scripts/render.py promote $(ARGS)

render-rollback:
	cd $(BACKEND) && uv run python ../scripts/render.py rollback $(ARGS)

# On-call worker (issue #19). State stays in ON_CALL_STATE_DIR, outside git.
on-call:
	cd $(BACKEND) && uv run python ../on-call/worker.py $(ARGS)

audit:
	cd $(BACKEND) && uv run pip-audit
	cd $(FRONTEND) && npm audit --omit=dev
