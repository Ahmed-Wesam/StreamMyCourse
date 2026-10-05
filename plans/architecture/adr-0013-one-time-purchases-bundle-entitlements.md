# ADR 0013 — One-Time Purchases and Bundle Entitlements (RS-5)

> **Payment provider / currency:** HyperPay COPYandPAY in **JOD** ([ADR 0015](./adr-0015-hyperpay-copyandpay-jod.md)) supersedes PayTabs / **USD** sections below for PSP and currency. Entitlement rules, cart metadata, and checkout precheck in this ADR remain normative.

## Status

Accepted (Research Spectrum)

**Supersedes:** subscription access rules in [`plans/billing/access-policy-v1.md`](../billing/access-policy-v1.md) (historical WS5 / pre-migration **015**).

## Context

Early billing work modeled **monthly subscription** unlock of all published courses (JOD, Jordan-focused PayTabs profile). Research Spectrum product direction changed to **USD one-time** purchases: per-course list price plus a platform **bundle** that grants all published courses (including courses published after purchase). Subscription tables and routes must not remain the access path.

## Decision

Ship **purchase-based entitlements** as the sole student unlock path for published courses (owners/admins still bypass).

### Product rules

- **Currency:** USD list prices in **cents** (`courses.price_amount_minor`); PayTabs HPP `cart_currency=USD`.
- **Products:** single **course** purchase, or platform **bundle** (`bundle_offers`) that grants access to **all published** courses at read time (full bundle price even if the student already owns some courses).
- **Checkout:** signed-in only; browser return does **not** grant access — **IPN → SQS → fulfillment** is source of truth; refund IPN revokes via `previous_tran_ref`.
- **Enrollments** do not grant lesson access (analytics/history only), consistent with the old policy’s enrollment exclusion but with purchases replacing subscriptions.

### Catalog domain

- Bounded context: `services/purchases/` — `CourseAccessService.has_course_access`, checkout precheck, price/bundle manage APIs, internal fulfillment hooks.
- **Removed:** `services/subscription/` and subscription HTTP routes; migration [`015_one_time_purchases.sql`](../../infrastructure/database/migrations/015_one_time_purchases.sql) adds `purchases` / `bundle_offers` / course price and drops `user_subscriptions` / `subscription_plans`.

### Billing edge

- Non-VPC billing edge creates one-time sale sessions and emits `purchase.paid|failed|revoked` fulfillment events (same no-NAT pattern as other edge workers). Catalog enqueues/consumes through existing billing SQS wiring — no PayTabs HTTP from the VPC Lambda.

### Access predicate (normative)

```text
has_course_access(user_sub, course_id, role) :=
  is_owner_or_admin(...)
  OR (
    course.status = 'PUBLISHED'
    AND (paid_course_purchase(user_sub, course_id) OR paid_bundle(user_sub))
  )
```

Missing purchase → API surfaces **`purchase_required`** (student checkout UX).

## Consequences

### Pros

- Matches Research Spectrum commercial model; one entitlement story in catalog and SPA.
- Clear supersession of subscription schema avoids dual access paths.
- Keeps payment provider I/O outside the VPC catalog Lambda.

### Cons

- Live PayTabs USD profile is an ops prerequisite (mock remains default pre-rollout).
- Bundle “all published now and later” is intentional and must stay documented for support/refunds.

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| Keep subscription + add à-la-carte | Dual entitlement logic and leftover JOD/subscription schema |
| Grant access on browser return URL | Spoofable; IPN must remain authority |
| Feature flag `BILLING_ENABLED` | Rejected; undeployed/missing secrets → `billing_unconfigured` is enough |

## Related

- [`design.md`](../../design.md) §13 #6
- [`plans/billing/access-policy-v1.md`](../billing/access-policy-v1.md) (superseded note)
- [`module-map.md`](./module-map.md) — `services/purchases/`, `services/billing_merchant/`
- ADR 0014 (RS-6 auth) — checkout requires signed-in student identity
