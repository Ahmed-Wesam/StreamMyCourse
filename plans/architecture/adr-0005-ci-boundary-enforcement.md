# ADR 0005 — CI boundary enforcement for the Lambda package

## Status

Accepted

## Context

Folder structure alone does not prevent architectural drift (“boundary erosion”).

## Decision

Add `scripts/check_lambda_boundaries.py` and run it in CI to block:

- `boto3` imports outside approved adapter files
- cross-imports between `services/course_management` and `services/auth`
- service importing HTTP helpers

## Consequences

- PRs fail fast when boundaries regress.
- Rules must be updated intentionally when new adapters/contexts are added.
