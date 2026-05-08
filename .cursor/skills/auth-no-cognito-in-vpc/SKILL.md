---
name: auth-no-cognito-in-vpc
description: Enforces StreamMyCourse auth design: controllers extract sub/role from API Gateway authorizer claims and pass them into services; the catalog Lambda (VPC) must not call Cognito or verify tokens via Cognito endpoints. Use when changing auth/authorization, touching controller/service boundaries, or when tempted to call Cognito from inside the VPC or catalog Lambda.
---

# Auth philosophy: no Cognito calls in VPC (catalog Lambda)

## Core rule (non-negotiable)

- **Do not call Cognito from inside the VPC or from the catalog Lambda** (`infrastructure/lambda/catalog/**`).
  - No `boto3.client("cognito-idp")` / AdminGetUser / ListUsers / GetUser calls.
  - No HTTP calls to Cognito from the catalog Lambda.
  - No “verify JWT by calling Cognito” from the catalog Lambda.

Rationale: the catalog Lambda runs in a VPC; Cognito access requires NAT/VPC endpoints and adds cost/latency. The repo’s intended design is that **authentication happens at the controller boundary** (API Gateway / authorizer), and the **service layer only consumes `sub` + `role`** for authorization logic.

## Required architecture pattern

- **Controller responsibility**:
  - Extract `sub` and `role` from **API Gateway authorizer claims** (trusted context).
  - Pass `cognito_sub` + `role` into services.
  - Enforce “must be authenticated” (non-empty `sub`) for non-public endpoints.

- **Service responsibility**:
  - Implement authorization rules using **only**:
    - `cognito_sub` (string) + `role` (string)
    - course ownership (`createdBy`)
    - enrollment state (repo)
    - course status (`DRAFT`/`PUBLISHED`)
  - Services must **not** fetch user identity/roles from Cognito.

- **Repository responsibility**:
  - Persist and query ownership/enrollment; no user directory lookups.

## Allowed exceptions

- **Only allowed**: verifying a JWT **offline** inside the Lambda (JWKS signature verification) *if and only if*:
  - it does **not** require calling Cognito APIs, and
  - it is used strictly to recover claims when an API Gateway authorizer is intentionally absent on a public route, and
  - it remains fail-secure (invalid token → anonymous).

If offline verification is needed, prefer a shared helper under `services/common/` and keep it small, cached, and deterministic.

## What to do instead of calling Cognito

When you need `sub`/`role`:

1. **Use API Gateway authorizer claims** (`event.requestContext.authorizer`).
2. If an endpoint is public but still needs to *optionally* scope draft access for authenticated callers:
   - Keep the endpoint public at API Gateway.
   - **Optionally** perform offline JWT verification in-Lambda (no Cognito calls) to recover `sub`/`role`.
   - Apply draft scoping using recovered `sub`/`role`.

## Review checklist (use before merging auth-related changes)

- [ ] Controllers pass `cognito_sub` and `role` into services; services do not reach out to Cognito.
- [ ] No imports/usages of `boto3.client("cognito-idp")` anywhere under `infrastructure/lambda/catalog/**`.
- [ ] No new network calls from the catalog Lambda to Cognito.
- [ ] Public endpoints that need optional identity use offline JWT verification only (no Cognito).
- [ ] Unit/integration tests cover:
  - anonymous behavior (published-only, no playback)
  - owner teacher/admin behavior on drafts
  - student behavior (published reads allowed; mutations denied)

