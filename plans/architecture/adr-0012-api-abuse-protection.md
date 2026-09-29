# ADR 0012 — Layered API Abuse Protection

## Status

Accepted (MVP)

## Context

Public and authenticated catalog routes need product-level request limits (progress bursts, playback, contact spam, certificate verify) without standing up a costly edge WAF for volumetric attack absorption. The catalog Lambda already uses RDS; API Gateway can apply coarse stage throttles.

## Decision

Use a **two-layer** model; **do not** rely on AWS WAF Web ACLs for this product (WAF stacks were removed for cost after a short trial).

### Layer 1 — Product policy (RDS counters)

- Bounded context: `services/rate_limit/` (policies, service, RDS repo, HTTP helpers).
- Middleware in `index.py` resolves route policies and increments counters in PostgreSQL (`014_rate_limit_counters.sql`).
- Denied requests return **429** with `Retry-After` when applicable; middleware logs `rate_limit_denied`.
- **Fail closed:** RDS/store errors → **503** `rate_limit_store_unavailable` (do not silently allow bursts).
- Operators may tune ceilings via optional `RATE_LIMIT_MAX_OVERRIDES` (CSV) in `config.py` without a feature kill-switch.

Representative policies (see `policies.py` for the live table): progress/playback/quiz per actor and resource; enroll; catalog actor burst; `contact.ip` / `contact.global`; certificate verify IP/global; research-team requirements and apply.

### Layer 2 — Volumetric abuse (API Gateway)

- `CatalogApiStage.MethodSettings` stage throttles on `api-stack.yaml`.
- `CatalogApi4xxAlarm` CloudWatch alarm on API Gateway `4XXError` (`CatalogApi4xxAlarmThreshold`).

### Explicit non-decision

- **No WAF** in the default architecture. Prefer RDS limits + Gateway throttles; revisit WAF only with a documented cost/incident justification.

## Consequences

### Pros

- Per-route product semantics (who is limited, which key) stay in application code and tests.
- Fail-closed store behavior avoids “open when broken.”
- Lower fixed cost than Web ACL + rule groups for current scale.

### Cons

- RDS counters add write load and a dependency on migration apply.
- Stage throttles are coarse; they do not replace carefully tuned per-route policies.
- No L7 bot scoring that WAF managed rules would provide.

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| AWS WAF on API / CloudFront | Cost vs benefit at MVP scale; stacks removed 2026-05-29 |
| In-memory / Lambda-only counters | Lost across cold starts and multi-instance; inconsistent limits |
| Fail-open on store error | Would defeat abuse protection during outages |

## Related

- [`design.md`](../../design.md) §9 Security
- [`module-map.md`](./module-map.md) — `services/rate_limit/`
- [`ImplementationHistory.md`](../../ImplementationHistory.md) — API abuse protection + WAF removal
