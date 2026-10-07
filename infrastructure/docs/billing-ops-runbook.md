# Billing ops runbook (HyperPay, JOD one-time purchases)

**Stack:** `StreamMyCourse-Payments-prod` ([`payments-stack.yaml`](../templates/payments-stack.yaml))  
**Decision records:** [ADR-0013](../../plans/architecture/adr-0013-one-time-purchases-bundle-entitlements.md) (entitlements), [ADR-0015](../../plans/architecture/adr-0015-hyperpay-copyandpay-jod.md) (HyperPay / JOD).

**Scope:** One-time **course** or **bundle** checkout; access follows RDS **`purchases`** (`paid` / `revoked`). Subscription tables were removed (migration **015**). Prices are **JOD fils** (whole dinars only; migration **024**).

---

## Architecture (no NAT)

| Component | VPC | Role |
|-----------|-----|------|
| Catalog Lambda | **In VPC** | Checkout precheck, price manage, internal fulfillment — **no** outbound HyperPay HTTP |
| Billing edge Lambda | **No VPC** | `POST /billing/checkout-session`, decrypt **`POST /webhooks/payments/hyperpay`** → enqueue SQS |
| Billing fulfillment Lambda | In VPC | Apply `purchase.paid|failed|revoked` to RDS |

---

## Environment (billing edge)

| Variable | Purpose |
|----------|---------|
| `PAYMENT_PROVIDER` | `mock` (no outbound OPPWA) or `hyperpay` (live/test entity) |
| `HYPERPAY_SECRET_ARN` | Secrets Manager ARN — preferred on prod |
| `HYPERPAY_ACCESS_TOKEN` / `HYPERPAY_ENTITY_ID` | Optional inline (CI/local); prod uses SM |
| `HYPERPAY_WEBHOOK_SECRET` | GitHub **`prod`** secret — HyperPay portal webhook encryption key (64-char hex per [their docs](https://hyperpay.docs.oppwa.com/tutorials/webhooks)); mirrored to SM `webhook_secret` and billing edge Lambda env on deploy |
| `BILLING_SHOPPER_RESULT_URL` | Student SPA **`https://<student-host>/billing/result`** (HyperPay `shopperResultUrl`) |

Deploy sets `BILLING_SHOPPER_RESULT_URL` from the edge stack **StudentSiteUrl** ([`deploy-backend.sh`](../../scripts/deploy-backend.sh), [`deploy-payments.sh`](../../scripts/deploy-payments.sh)). Deploy **must not** pass an empty value (that disables HyperPay). If checkout returns **503** `billing_unconfigured` with **OPTIONS** also failing, verify this env on **StreamMyCourse-BillingEdge-prod**.

---

## Secrets Manager

**Name:** `streammycourse/hyperpay/prod` (override with `HYPERPAY_SECRET_ID` in [`ensure-hyperpay-secret.sh`](../../scripts/ensure-hyperpay-secret.sh)).

**JSON shape (no secrets in tickets):**

```json
{
  "access_token": "<Bearer token from HyperPay back office>",
  "entity_id": "<Channel entity id>",
  "api_host": "eu-test.oppwa.com",
  "webhook_secret": "<64 hex chars>"
}
```

**GitHub Environment `prod` secrets (operator):**

- `HYPERPAY_ACCESS_TOKEN`
- `HYPERPAY_ENTITY_ID`
- `HYPERPAY_WEBHOOK_SECRET`

Deploy job runs `ensure-hyperpay-secret.sh` before payments stack update. **Do not commit tokens.**

---

## HyperPay test vs production

| Mode | API host | When |
|------|----------|------|
| **Test** | `eu-test.oppwa.com` | Default in SM `api_host`; use test entity + test cards |
| **Production** | `eu-prod.oppwa.com` | Live entity after HyperPay production approval |

**Test cards (Research Spectrum test entity on `eu-test.oppwa.com`; amounts must be whole JOD, e.g. `50.00`):**

| PAN | Expiry | CVV | Result |
|-----|--------|-----|--------|
| **4012000033330026** | 01/39 | 100 | Success (Visa) |
| **5123450000000008** | 01/39 | 100 | Success (Mastercard) |
| **5204730000002514** | 01/39 | 251 | Fail |

Cardholder name: any name.

Use only on **`eu-test.oppwa.com`**. Checkout **`POST /v1/checkouts`** from the billing edge includes **`testMode=EXTERNAL`** and **`customParameters[3DS2_enrolled]=true`** on that host only (HyperPay test entity setup). Student widget brands: **VISA**, **MASTER** ([`HyperPayWidget.tsx`](../../frontend/src/components/billing/HyperPayWidget.tsx)).

**Canonical list prices:** **50 JOD** per course (`50_000` fils), **150 JOD** bundle (`150_000` fils) unless instructors change published prices.

---

## Webhook URL (register with HyperPay)

HyperPay sends **encrypted** `POST` notifications. Register in the HyperPay back office (exact menu varies):

```text
https://<api-gateway-host>/<stage>/webhooks/payments/hyperpay
```

Example prod pattern: resolve **`ApiEndpoint`** from `StreamMyCourse-Api-prod` stack output + stage name (typically `prod`).

**Headers (HyperPay → API Gateway):**

- Body: hex-encoded ciphertext
- `X-Initialization-Vector`
- `X-Authentication-Tag`

**Verification:** webhook secret in SM must match HyperPay portal. Mismatch → **401** `invalid_webhook`. Missing secret on edge → **503** `billing_unconfigured`.

**Activation (HyperPay back office):** HyperPay may send a probe `POST` without `X-Initialization-Vector` / `X-Authentication-Tag`. The billing edge responds **200** `{"status":"ok"}` and does **not** enqueue. Real notifications include both headers and encrypted body.

**Integration tests:** set **`INTEGRATION_HYPERPAY_WEBHOOK_SECRET`** (or `HYPERPAY_WEBHOOK_SECRET`) to the same hex key — never log the value. See [`tests/integration/README.md`](../../tests/integration/README.md).

---

## Mock provider (`PAYMENT_PROVIDER=mock`)

**Invariant:** No outbound OPPWA HTTP; checkout returns fixed **`checkoutId`** `MOCK-HP-CHECKOUT` and mock widget URL.

| Check | Where |
|-------|--------|
| Deploy var | GitHub Environment **`PAYMENT_PROVIDER`** = `mock` (pre-go-live) |
| Runtime | Lambda **`StreamMyCourse-BillingEdge-prod`** env **`PAYMENT_PROVIDER`** |

```bash
aws lambda get-function-configuration \
  --function-name "StreamMyCourse-BillingEdge-prod" \
  --query 'Environment.Variables.PAYMENT_PROVIDER' --output text
```

Encrypted webhooks still require **`HYPERPAY_WEBHOOK_SECRET`** (or SM `webhook_secret`) even in mock mode.

---

## Student checkout flow (support)

1. Signed-in **`POST /billing/checkout-session`** `{ "productType": "course"|"bundle", "courseId"? }`.
2. Response includes **`checkoutId`**, **`widgetScriptUrl`**, **`integrity`**, **`shopperResultUrl`**, **`amountMinor`**, **`currency": "JOD"`**.
3. Student pays in embedded widget; browser returns to **`/billing/result?id=<checkoutId>`**.
4. SPA polls **`GET /billing/purchases`** until the pending row is **`paid`** (HyperPay **`POST /webhooks/payments/hyperpay`** → SQS → fulfillment). Do not use HyperPay **`GET /payment`** from the browser.
5. HyperPay **`POST /webhooks/payments/hyperpay`** → SQS → fulfillment marks **`purchases`** `paid`.

Missing purchase → playback **403** `purchase_required`.

---

## Fulfillment DLQ triage

| Resource | Name pattern |
|----------|----------------|
| DLQ | `StreamMyCourse-BillingFulfillment-DLQ-{env}` |
| Primary queue | `StreamMyCourse-BillingFulfillment-{env}` |
| Fulfillment Lambda | `StreamMyCourse-BillingFulfillment-{env}` |
| DLQ alarm | `StreamMyCourse-BillingFulfillment-DLQ-{env}-Visible` |
| SNS (DLQ + edge errors) | `StreamMyCourse-BillingFulfillment-Alerts-{env}` |

**Alarm:** `ApproximateNumberOfMessagesVisible` on the DLQ **> 0** (5‑minute period) → SNS topic shared with billing edge error alarm.

### Triage steps

1. **Confirm env** — stack `StreamMyCourse-Payments-{env}`, account, region.
2. **Sample one DLQ message** — do not paste full bodies with PII into tickets.
3. **Correlate** — CloudWatch `/aws/lambda/StreamMyCourse-BillingFulfillment-{env}` at message time; RDS errors, idempotency, bad payload.
4. **Classify** — transient (redrive after fix) vs poison (fix parser/code first).
5. **Student impact** — access follows **`purchases`**, not queue depth; DLQ backlog means paid webhooks may not have applied yet.

Optional stack param **`BillingFulfillmentAlertEmail`** subscribes SNS at deploy.

---

## Billing edge Errors alarm

| Resource | Name pattern |
|----------|----------------|
| Alarm | `StreamMyCourse-BillingEdge-{env}-Errors` |
| Metric | Lambda **`Errors`** · **`StreamMyCourse-BillingEdge-{env}`** |
| Threshold | Sum ≥ 1 over **86400 s** |
| Action | `StreamMyCourse-BillingFulfillment-Alerts-{env}` |

**Triage:** Logs `/aws/lambda/StreamMyCourse-BillingEdge-{env}` — filter by route:

- `POST /billing/checkout-session` — catalog precheck / `billing_unconfigured`
- `POST /webhooks/payments/hyperpay` — decrypt / parse / enqueue (activation probe without IV/tag → **200**, no enqueue)

---

## Legal page URLs (merchant / HyperPay profile)

Paste into HyperPay or merchant **terms** / **privacy** fields after student SPA is live:

| Env | Terms | Privacy |
|-----|-------|---------|
| **prod** | `https://researchspectrum.org/terms` | `https://researchspectrum.org/privacy` |

Teachers copy from **Payment setup** (`/settings/payments`) if preferred.

---

## Go-live checklist (follow HyperPay email order)

**Phase 1 — COPYandPAY (Zaid test credentials)**

1. **GitHub `prod` secrets:** `HYPERPAY_ACCESS_TOKEN`, `HYPERPAY_ENTITY_ID` only; `ensure-hyperpay-secret.sh` → SM **`streammycourse/hyperpay/prod`** (`api_host`: `eu-test.oppwa.com`).
2. **`PAYMENT_PROVIDER=hyperpay`**; redeploy payments + API stacks.
3. **Smoke:** student checkout → widget on `eu-test.oppwa.com` → return URL → webhook marks purchase **`paid`** → playback **200** (test cards from runbook).

**Phase 2 — Webhooks (only after HyperPay Administration → Webhooks)**

4. Configure URL `https://<api-endpoint>/<stage>/webhooks/payments/hyperpay` and **their** 64-hex secret in back office; copy the same secret into SM `webhook_secret` / `HYPERPAY_WEBHOOK_SECRET`, redeploy edge.
5. **Email Zaid** if they must activate the webhook on their side.

**Ops**

6. **Alarms:** SNS on `StreamMyCourse-BillingFulfillment-Alerts-prod`.

---

## Related alarms (cost only)

Monthly **billing cost** alarm: [`billing-alarm.yaml`](../templates/billing-alarm.yaml) — not purchase fulfillment.
