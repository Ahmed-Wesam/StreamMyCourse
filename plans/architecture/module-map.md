# StreamMyCourse — Module map (Lambda package)

This document is the “public surface” map for the Python Lambda under `infrastructure/lambda/catalog/`.

## Composition / entry

| Module | Responsibility | Public API |
|--------|----------------|------------|
| `index.py` | Lambda entrypoint | `lambda_handler` |
| `bootstrap.py` | Dependency wiring (composition root) | `lambda_bootstrap()` |
| `config.py` | Environment configuration | `load_config()`; `pick_origin` helpers live in `services/common/http.py` |

## Bounded contexts

### `services/course_management/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | Parses API Gateway events, maps errors to JSON, returns API responses |
| `service.py` | Domain/application | Business rules; depends on **ports** only |
| `repo.py` | Persistence adapter (DynamoDB) | Legacy DynamoDB access; PK/SK mapping stays here (rollback path while `USE_RDS=false`) |
| `rds_repo.py` | Persistence adapter (PostgreSQL) | psycopg2-based adapter selected when `USE_RDS=true`; same `CourseCatalogRepositoryPort` |
| `storage.py` | Infrastructure adapter | S3 presign generation |
| `ports.py` | Contracts | `Protocol` interfaces for repo/storage |
| `models.py` | Domain models | Persistence-agnostic domain types |
| `contracts.py` | API DTOs | TypedDicts for JSON shapes returned by controller |

**Cross-context rule:** `course_management` must not import `services.auth` (enforced in CI).

### `services/auth/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | `/users/me` handler |
| `service.py` | Domain/application | Depends on `UserProfileRepositoryPort` |
| `ports.py` | Contracts | `UserProfileRepositoryPort` Protocol (shared by DynamoDB and RDS adapters) |
| `repo.py` | Persistence adapter (DynamoDB) | `UserProfileRepository` -- rollback path |
| `rds_repo.py` | Persistence adapter (PostgreSQL) | `UserProfileRdsRepository` -- active under `USE_RDS=true` |

**Cross-context rule:** `auth` must not import `course_management` (enforced in CI).

### `services/enrollment/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `ports.py` | Contracts | `EnrollmentRepositoryPort` |
| `repo.py` | Persistence adapter (DynamoDB) | |
| `rds_repo.py` | Persistence adapter (PostgreSQL) | Idempotent upserts via `ON CONFLICT DO NOTHING` |

### `services/common/` (shared kernel)

Cross-cutting utilities shared by multiple contexts:

- `errors.py` — typed HTTP errors (`HttpError` hierarchy)
- `http.py` — CORS + JSON response helpers
- `validation.py` — strict JSON parsing + simple validators

## What other modules may import

- Controllers may import `services/common/*` and their own `contracts.py`.
- Services may import `ports.py`, `models.py`, and `services/common/errors.py` (not HTTP helpers).
- Repos/storage may import `boto3` and Dynamo/S3 specifics.
- `rds_repo.py` modules may import `psycopg2`; no other module may (enforced in CI).
- `bootstrap.py` may import both `boto3` (Secrets Manager) and `psycopg2` (connection) -- it is the composition root.

## Enforcement

- Cursor rule: `.cursor/rules/clean-architecture-boundaries.mdc`
- CI script: `scripts/check_lambda_boundaries.py` (runs in GitHub Actions)
