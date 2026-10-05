# ADR 0015 — HyperPay COPYandPAY, JOD One-Time Purchases

## Status

Accepted (Research Spectrum)

**Supersedes:** PayTabs HPP / **USD** payment-provider and currency decisions in [ADR 0013](./adr-0013-one-time-purchases-bundle-entitlements.md) (entitlement rules in 0013 remain normative).

## Context

Research Spectrum operates in **Jordan** with **JOD** list prices. PayTabs USD HPP did not match merchant setup, legal copy, or instructor pricing UX. HyperPay **COPYandPAY** embeds a PCI-scoped widget on the student checkout page; the platform still must keep payment HTTP **outside** the in-VPC catalog Lambda (no NAT).

Product model is unchanged from ADR 0013: **one-time** per-course purchase or platform **bundle**; access via RDS **`purchases`**; browser return is **not** authoritative — webhook (and optional checkout-status poll) → SQS → fulfillment.

## Decision

### Currency and list prices

- **Currency:** **JOD** only for checkout and RDS purchase rows.
- **Minor units:** **fils** (`1 JOD = 1000 fils`); API field **`amountMinor`**.
- **Whole dinars only:** course and bundle prices must be multiples of **1000** fils (migration [`024_hyperpay_jod.sql`](../../infrastructure/database/migrations/024_hyperpay_jod.sql)).
- **Canonical defaults:** **50 JOD** per course (`50_000` fils), **150 JOD** bundle (`150_000` fils) where seeded.

### Payment provider

- **HyperPay** (OPPWA) **COPYandPAY**: `POST /v1/checkouts` → **`checkoutId`** + widget script URL + **integrity** hash; student SPA embeds [`HyperPayWidget`](../../frontend/src/components/billing/HyperPayWidget.tsx).
- **Test host:** `eu-test.oppwa.com`; production host `eu-prod.oppwa.com` (from Secrets Manager `api_host` when set).
- **Mock adapter:** `PAYMENT_PROVIDER=mock` on the billing edge — no outbound OPPWA HTTP; fixed `MOCK-HP-CHECKOUT` for CI and pre-go-live prod.

### Browser return vs webhook

- **`shopperResultUrl`:** student SPA **`/billing/result`** (legacy `/billing/success` redirects). Query param **`id`** = HyperPay checkout id; client calls **`POST /billing/checkout-status`** to poll payment result (does not grant access by itself).
- **Authority:** encrypted **`POST /webhooks/payments/hyperpay`** → billing edge decrypt (AES-GCM) → domain events → fulfillment SQS → catalog internal hooks (same RS-5 purchase fulfillment as ADR 0013).

### Billing edge (no VPC)

- Package: [`infrastructure/lambda/billing_edge/`](../../infrastructure/lambda/billing_edge/).
- Stack: [`payments-stack.yaml`](../../infrastructure/templates/payments-stack.yaml) — **no VPC**, no NAT; invokes catalog for checkout precheck; enqueues fulfillment messages only.
- Secrets: **`streammycourse/hyperpay/{env}`** (JSON: `access_token`, `entity_id`, optional `webhook_secret`, `api_host`); GitHub prod secrets **`HYPERPAY_ACCESS_TOKEN`**, **`HYPERPAY_ENTITY_ID`**, **`HYPERPAY_WEBHOOK_SECRET`** hydrated by [`ensure-hyperpay-secret.sh`](../../scripts/ensure-hyperpay-secret.sh).
- **`merchantTransactionId`** cart encoding unchanged (v2 purchase carts): `v2|{env}|{userSub}|course|{courseId}|{purchaseId}` or `v2|{env}|{userSub}|bundle|{purchaseId}`.

### Catalog (in VPC)

- Checkout precheck and price manage remain in **`services/purchases/`**; internal **`billing.checkout`** invoke returns **`currency: JOD`** and fils **`amount_minor`**.
- Catalog does **not** call HyperPay.

## Consequences

### Pros

- Aligns PSP, currency, and legal/marketing copy with Jordan operations.
- COPYandPAY keeps card data off the SPA origin while preserving a single checkout page.
- Reuses RS-5 entitlement and fulfillment pipeline; only the edge adapter and frontend widget changed.

### Cons

- Operators must register webhook URL and rotate **64-char hex** webhook secret with HyperPay.
- Live go-live requires test → prod entity migration and smoke on real cards (test cards on `eu-test.oppwa.com` only).

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| Keep PayTabs USD | Wrong currency and merchant profile for Research Spectrum |
| Stripe | Not the chosen regional PSP; ADR 0013 already rejected subscription-first Stripe |
| Grant access on `/billing/result` only | Spoofable; webhook + fulfillment remain source of truth |

## Related

- [ADR 0013](./adr-0013-one-time-purchases-bundle-entitlements.md) — purchase entitlements (still normative for access)
- [`design.md`](../../design.md) §13 #6, student routes `/checkout`, `/billing/result`
- [`infrastructure/docs/billing-ops-runbook.md`](../../infrastructure/docs/billing-ops-runbook.md)
- [`module-map.md`](./module-map.md) — `billing_edge`, `services/purchases/`
