.PHONY : install test test-dist lint

POETRY := $(shell command -v poetry 2> /dev/null)

all: install test

install:
	${POETRY} install

test:
	${POETRY} run pytest

test-dist:
	${POETRY} run pytest -n auto
