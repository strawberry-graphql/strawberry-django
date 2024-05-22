---

We use [poetry](https://github.com/sdispater/poetry) to manage dependencies, to
get started follow these steps:

```shell
git clone https://github.com/strawberry-graphql/strawberry-django.git
cd strawberry_django
poetry install
poetry run pytest
```

This will install all the dependencies (including the dev ones) and run the tests.

If the tests fail with `SpatiaLite requires SQLite to be configured to allow extension loading` error,
it means that your python interpreter is not built with `--enable-loadable-sqlite-extensions` flag.
For example, if you are using pyenv, it can be fixed like this:

`PYTHON_CONFIGURE_OPTS="--enable-loadable-sqlite-extensions" pyenv install 3.12.0`

### Pre commit

We have a configuration for
[pre-commit](https://github.com/pre-commit/pre-commit), to add the hook run the
following command:

```shell
pre-commit install
```

### Docs setup and local server

We use Material for MkDocs, you can read the documentation [here](https://squidfunk.github.io/mkdocs-material/)

```shell
make serve-docs
```
