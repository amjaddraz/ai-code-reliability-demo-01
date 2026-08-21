# AI-Generated Order API Regression

**Demonstration Project**

## Context

This deliberately small FastAPI and SQLAlchemy application represents a
realistic reliability problem in AI-assisted development: code can appear to
support idempotent requests while placing the idempotency decision too late to
prevent duplicate side effects.

The project is a controlled engineering demonstration, not paid client work.
Its narrow scope makes the investigation, regression test, correction, and
verification easy to inspect independently.

## Reported Problem

An order request includes a `client_request_id` so an exact retry can resolve
to the original order. Correct behavior requires one persisted order and one
inventory reduction, even if the request is submitted twice.

The reported behavior suggested that the response looked correct while order
and inventory side effects were repeated.

## Baseline

The original suite passed:

```text
9 passed, 1 warning
```

That green result did not establish retry correctness. The tests covered
single order creation, one inventory reduction, validation errors, and listing
orders with different request IDs. None submitted the same
`client_request_id` twice.

The warning was present at baseline and came from the installed test-client
stack; it was unrelated to order behavior.

## Reproduction

The behavior was reproduced with the existing isolated `TestClient` and
in-memory SQLite setup:

- A product started with stock 10.
- The same order payload, with quantity 2 and a fixed
  `client_request_id`, was submitted twice sequentially.
- Both HTTP responses returned the original order ID.
- Two order rows persisted instead of one.
- Stock changed from 10 to 6 instead of from 10 to 8.

A focused regression test was added before production code changed. It failed
because the API listed two persisted orders where one was expected:

```text
FAILED tests/test_orders.py::test_repeated_client_request_does_not_create_duplicate_order
AssertionError: assert 2 == 1
1 failed, 1 warning
```

## Root Cause

Order creation performed its operations in the wrong sequence. It loaded and
validated the product, reduced inventory, created and flushed a new `Order`,
and only then searched for an earlier order with the same
`client_request_id`.

When the earlier order was found, the transaction containing the new order and
second stock reduction was still committed. The function then returned the
earlier order object. This made the second HTTP response appear correct while
the database contained duplicate side effects.

## Fix

The correction was deliberately small:

- Resolve `client_request_id` before product lookup or any side effect.
- Return the original order immediately when the product and quantity match.
- Return HTTP 409 Conflict when the same ID is reused with different order
  data.
- Remove the duplicate lookup that previously ran after mutation and order
  creation.

No concurrent-request hardening, database uniqueness constraint, migration,
dependency change, or architectural redesign was included.

## Verification

### Focused regression validation

After the fix, the original retry regression passed:

```text
1 passed, 1 warning in 0.03s
```

It verifies that two identical sequential requests resolve to the same order,
leave one persisted order, and reduce stock only once.

### Adversarial validation

The focused idempotency set then passed four cases:

```text
4 passed, 1 warning in 0.07s
```

Coverage included:

- An exact retry after the first request exhausted inventory, proving the
  existing order is resolved before stock validation.
- Reuse with a different quantity of 11, which also exceeded remaining stock,
  proving the idempotency conflict takes precedence over stock validation.
- Reuse with a different product, proving no unintended product inventory is
  changed.
- The original sequential retry regression.

### Full regression

The complete expanded suite passed:

```text
13 passed, 1 warning in 0.18s
```

No new failures appeared. The one warning was the same unrelated warning seen
in the original baseline.

## Before / After

| Behavior | Before | After |
| --- | --- | --- |
| Exact sequential retry responses | Both returned original order ID | Both return original order ID |
| Persisted orders after retry | 2 | 1 |
| Stock after two quantity-2 submissions from 10 | 6 | 8 |
| Same request ID with different order data | No explicit conflict behavior was defined or covered by the original tests | HTTP 409 Conflict, no additional side effect |
| Complete test suite | 9 passed, 1 warning | 13 passed, 1 warning |

## Files Changed

- `app/services/orders.py`: moved idempotency resolution ahead of product and
  order side effects and added the conflicting-reuse business exception.
- `app/main.py`: translated conflicting request-ID reuse to HTTP 409.
- `tests/test_orders.py`: added the sequential regression and adversarial
  retry/conflict coverage.
- `evidence/baseline.txt`: records the original test baseline.
- `evidence/reproduction.txt`: records the failing reproduction and observed
  database state.
- `evidence/full-regression.txt`: records the final complete-suite result.
- `CASE_STUDY.md`: documents the investigation and verified outcome.
- `README.md`: points readers to this case study and its Git milestones.

## Remaining Uncertainty

- Concurrent retries were not validated.
- No database-level unique constraint was added for `client_request_id`.
- No migration strategy was implemented.
- Production database locking and isolation behavior was not proven.
- Sequential SQLite tests do not establish distributed concurrency safety.

## Result

The demonstrated sequential retry defect is fixed and covered by regression
and adversarial tests. Exact retries return the original order without another
order row or stock reduction, and conflicting reuse returns HTTP 409. The
expanded 13-test suite passes with the same unrelated warning present at
baseline.

## Reproducing the Case

Two Git milestones make the change inspectable:

- `demo-broken-state`: the original verified defective baseline, where the
  existing suite passed 9 tests while the retry defect was still present.
- `demo-tested-fix`: the corrected state with focused, adversarial, and full
  regression validation.

The failing regression test and reproduction evidence were introduced in the
intermediate reproduction commit before the production fix. No additional tag
was created for that intermediate commit.

To inspect either state, check out the corresponding tag. Follow the local
setup in `README.md`, then run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider
```
