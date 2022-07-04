.PHONY : install test serve-docs lint

POETRY := $(shell command -v poetry 2> /dev/null)
MKDOCS := $(shell command -v mkdocs 2> /dev/null)

all: install test serve-docs

install:
	${POETRY} install

test:
	${POETRY} run pytest

serve-docs:
	poetry install --extras "docs"
	${MKDOCS} serve
