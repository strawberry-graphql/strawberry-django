.PHONY : install test lint

POETRY := $(shell command -v poetry 2> /dev/null)

all: install test

install:
	${POETRY} install

test:
	${POETRY} run pytest
