PYTHON ?= python

BACKEND := backend
FRONTEND := frontend

.PHONY: install dev test lint fmt

install:
	cd $(BACKEND) && uv sync
	cd $(FRONTEND) && npm ci

dev:
	$(PYTHON) scripts/dev.py

test:
	cd $(BACKEND) && uv run pytest
	cd $(FRONTEND) && npm run test

lint:
	cd $(BACKEND) && uv run ruff check .
	cd $(BACKEND) && uv run mypy app
	cd $(FRONTEND) && npm run lint
	cd $(FRONTEND) && npm run typecheck

fmt:
	cd $(BACKEND) && uv run ruff check --fix .
	cd $(BACKEND) && uv run ruff format .
	cd $(FRONTEND) && npm run format
