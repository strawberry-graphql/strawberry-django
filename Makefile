.PHONY : install test test-dist lint

all: install test

install:
	uv sync

test:
	uv run pytest

test-dist:
	uv run pytest -n auto

lint:
	uv run ruff check .
	uv run ruff format --check .
