# Quick start

Install poetry

```shell
pip install poetry
```

Install example example project dependencies, execute migrations and start development server.

```shell
cd examples/django
poetry install
poetry run ./manage.py migrate
poetry run ./manage.py runserver
```

After that you should have web server and graphql endpoint running at http://127.0.0.1:8000/graphql.
