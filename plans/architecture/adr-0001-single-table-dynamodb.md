# ADR 0001 — Single-table DynamoDB for the MVP catalog

## Status

Accepted (MVP)

## Context

We need durable course + lesson metadata with a small number of access patterns and minimal operational overhead.

## Decision

Use a single DynamoDB table with composite keys:

- `PK = COURSE#<id>`
- `SK = METADATA | LESSON#<order>`

## Consequences

- **Pros:** simple ops, low cost at MVP scale, one IAM resource, straightforward queries per course.
- **Cons:** listing all published courses may require `Scan` or a future GSI; cross-course queries need deliberate design.

## Follow-ups

See ADR 0006 (data access evolution) for when/how to add GSIs and remove `Scan`.
