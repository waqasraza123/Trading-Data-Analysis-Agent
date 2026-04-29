# Trading Intelligence API

Phase 1 provides the FastAPI, settings, database, Alembic, health, error handling, logging, and test foundation only.

## Commands

Install dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Run the development server:

```sh
.venv/bin/uvicorn app.main:app --reload
```

Run migrations:

```sh
.venv/bin/alembic upgrade head
```

Run tests:

```sh
.venv/bin/pytest
```

Run lint:

```sh
.venv/bin/ruff check .
```

Run typecheck:

```sh
.venv/bin/mypy app
```

## Schema Docs

The Phase 2 core schema is documented in:

```txt
docs/schema/core-schema.md
```

The Phase 3 configuration services are documented in:

```txt
docs/configuration-services.md
```
