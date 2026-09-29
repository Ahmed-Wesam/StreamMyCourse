# ADR 0011 — Video Provider Port and Kinescope Cutover

## Status

Accepted (MVP)

## Context

Lesson video upload, processing status, and playback must support a real DRM-capable provider without baking provider HTTP into every course-management call site. Constraints:

- Catalog Lambda runs **in-VPC without NAT** — it must not call public provider APIs directly.
- S3 (and legacy VdoCipher) adapters remain useful for local/dev and rollback.
- Playback and DRM auth still need enrollment/purchase access checks inside the catalog domain.

## Decision

Introduce a **`VideoProviderPort`** under `services/course_management/video_providers/` and default production to **Kinescope**.

### Port and adapters

- **Port:** `services/course_management/video_providers/port.py` — upload init, metadata, playback resolve, delete.
- **Adapters:** `kinescope_adapter.py` (default), `s3_video_provider.py`, `vdocipher_adapter.py` (retained).
- **Env:** `VIDEO_PROVIDER` (`kinescope` | `s3` | `vdocipher`); `config.py` defaults to `kinescope`.

### Webhooks and DRM

- `POST /webhooks/kinescope` — shared-secret webhook; mutating events re-checked against Kinescope GET `/videos/{id}` when token is configured; `done` → lesson `ready`, `error`/`aborted` → `failed`.
- `POST /webhooks/kinescope/drm-auth` — signed JWT (`KINESCOPE_DRM_JWT_*`) plus lesson-access authorization in catalog service.
- Playback returns a provider-discriminated payload (Kinescope: `videoId`, `drmAuthToken`, required `watermarkText` from Cognito claims; S3: `playbackUrl`).

### Video Provider Edge Lambda (no-VPC egress)

Outbound Kinescope HTTP lives in a **separate no-VPC** Lambda, not a per-provider microservice and not the VPC catalog:

| Piece | Location |
|-------|----------|
| Edge package | `infrastructure/lambda/video_provider_edge/` |
| Stack | `infrastructure/templates/video-provider-edge-stack.yaml` (`StreamMyCourse-VideoProviderEdge-*`) |
| Catalog bridge | `services/course_management/internal_video.py` + internal invoke from `index.py` |
| Route conditions | `api-stack.yaml` (`UseKinescopeVideoEdge`) |

When `VideoProviderEdgeLambdaArn` is set with `VIDEO_PROVIDER=kinescope`:

- **Edge** holds upload/webhook secrets (`KINESCOPE_API_TOKEN`, `KINESCOPE_PARENT_ID`, `KINESCOPE_WEBHOOK_SECRET`).
- **Catalog** keeps `KINESCOPE_DRM_JWT_*` for playback and `drm-auth` (access checks stay in-domain).
- Deploy order is encoded in `scripts/deploy-backend.sh` / `scripts/deploy-video-provider-edge.sh` (edge before api wiring that points routes at the edge ARN).

## Consequences

### Pros

- Domain code stays provider-agnostic; swapping default provider is an adapter + env change.
- No NAT for catalog; Kinescope HTTP is isolated to the edge worker.
- DRM/playback authorization remains in catalog (purchase/enrollment rules).

### Cons

- Two Lambdas and an internal invoke contract to operate and test.
- Env/secret split must stay aligned with api-stack conditions or upload/webhook routes fail closed.

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| Catalog calls Kinescope over NAT | Violates no-NAT cost/security invariant |
| One Lambda per video provider | Extra stacks/ops for MVP; port + one edge is enough |
| Provider SDK inside course `service.py` | Couples domain to vendor HTTP and breaks boundary checks |

## Related

- [`design.md`](../../design.md) §4 video pipeline, §7 playback/webhooks, §10 Backend
- [`module-map.md`](./module-map.md)
- [`ImplementationHistory.md`](../../ImplementationHistory.md) — Kinescope cutover + video provider edge closeouts
