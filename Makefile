PYTHON ?= python

BACKEND := backend
FRONTEND := frontend

.PHONY: install dev test e2e lint fmt seed seed-reset docker-up docker-down docker-build fly-create fly-db fly-secrets fly-deploy fly-verify fly-releases fly-rollback fly-validate

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

# Fly.io (issue #15): ENV=dev|prod selects the target for the commands that
# need one; setup and verify commands default to both environments.

fly-create:
	$(PYTHON) scripts/fly.py create $(ENV)

fly-db:
	$(PYTHON) scripts/fly.py db $(ENV)

fly-secrets:
	$(PYTHON) scripts/fly.py secrets $(ENV)

fly-deploy:
	$(PYTHON) scripts/fly.py deploy $(ENV)

fly-verify:
	$(PYTHON) scripts/fly.py verify $(ENV)

fly-releases:
	$(PYTHON) scripts/fly.py releases $(ENV)

fly-rollback:
	$(PYTHON) scripts/fly.py rollback $(ENV)

fly-validate:
	$(PYTHON) scripts/fly.py validate $(ENV)
