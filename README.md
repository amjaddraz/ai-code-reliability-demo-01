# Order Reliability Demonstration

This is a **Demonstration Project**: a deliberately small FastAPI backend built
as a scoped software-reliability case study. It provides products, inventory,
and order creation while documenting bug reproduction, root-cause analysis,
regression testing, and a verified correction.

## Scope

- Create and retrieve products.
- Create orders against available inventory.
- Reject invalid quantities, missing products, and insufficient stock.
- List created orders.
- Report application health.

The project intentionally excludes authentication, payments, deployment,
frontend concerns, and external services.

## Case study

See [CASE_STUDY.md](CASE_STUDY.md) for the reproduced regression, root-cause
analysis, minimal correction, and verification evidence. The Git tags
`demo-broken-state` and `demo-tested-fix` provide inspectable before-and-after
milestones.

## Local setup

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Run the test suite:

```bash
pytest
```

The application uses `orders.db` by default. Tests use an isolated, temporary
in-memory SQLite database and do not depend on the runtime database.
