# Billing ops runbook (WS8 — pre-go-live, mock on)

**Stack:** `StreamMyCourse-Payments-{dev|prod}` ([`payments-stack.yaml`](../templates/payments-stack.yaml))  
**Scope:** Subscription billing edge + fulfillment while **`PAYTABS_USE_MOCK=true`** on dev and prod. Live PayTabs flip is [WS9](../../plans/billing-workstream-9-paytabs-live-go-live.md).

**Contracts:** [manage-contract-v1](../../plans/billing/manage-contract-v1.md), [subscribe-contract-v1](../../plans/billing/subscribe-contract-v1.md), [access-policy-v1](../../plans/billing/access-policy-v1.md).

---

## Mock guard (`PAYTABS_USE_MOCK=true`)

**Invariant (WS8):** Both **dev** and **prod** must run the mock PayTabs adapter — **no outbound PayTabs HTTP**, no real charges.

| Check | Where |
|-------|--------|
| Deploy input | GitHub Environment variable **`PAYTABS_USE_MOCK`** = `true` on **dev** and **prod** ([`deploy-backend.yml`](../../.github/workflows/deploy-backend.yml)) |
| Runtime | Lambda **`StreamMyCourse-BillingEdge-{env}`** env **`PAYTABS_USE_MOCK`** = `true` |

**Verify (no secret values):**

```bash
# Replace {env} with dev or prod
aws lambda get-function-configuration \
  --function-name "StreamMyCourse-BillingEdge-{env}" \
  --query 'Environment.Variables.PAYTABS_USE_MOCK' --output text
```

Expect **`true`**. If `false` or missing on prod, **stop** and fix deploy vars before any go-live work.

**Do not** set `PAYTABS_USE_MOCK=false` until WS9 pre-flight is complete.

---

## Fulfillment DLQ triage

| Resource | Name pattern |
|----------|----------------|
| DLQ | `StreamMyCourse-BillingFulfillment-DLQ-{env}` |
| Primary queue | `StreamMyCourse-BillingFulfillment-{env}` |
| Fulfillment Lambda | `StreamMyCourse-BillingFulfillment-{env}` |
| DLQ alarm | `StreamMyCourse-BillingFulfillment-DLQ-{env}-Visible` |
| SNS (DLQ + edge errors) | `StreamMyCourse-BillingFulfillment-Alerts-{env}` |

**Alarm:** `ApproximateNumberOfMessagesVisible` on the DLQ **> 0** (5‑minute period) → same SNS topic as billing edge errors.

### Triage steps

1. **Confirm env** — stack `StreamMyCourse-Payments-{env}`, account, and region before touching queues.
2. **Sample one DLQ message** — SQS console or `receive-message` (do not log full bodies in tickets if they contain PII).
3. **Correlate** — CloudWatch log group `/aws/lambda/StreamMyCourse-BillingFulfillment-{env}` around the message timestamp; look for RDS errors, idempotency conflicts, or poison payloads.
4. **Classify**
   - **Transient** (timeout, throttling, DB blip): fix underlying issue, then **redrive** DLQ → primary queue only after the root cause is resolved.
   - **Bad payload / unknown event**: capture `provider_event_id` / event type from logs; fix parser or ignore-list in code before redrive.
   - **Duplicate / already applied**: fulfillment is idempotent; verify RDS `billing_subscription` / webhook ledger — message may be safe to delete after confirmation.
5. **Student impact** — access follows RDS `current_period_end` ([access-policy-v1](../../plans/billing/access-policy-v1.md)), not queue depth. DLQ backlog means **IPN/renewal state may lag**, not necessarily immediate loss of access.

Optional stack param **`BillingFulfillmentAlertEmail`** subscribes the SNS topic at deploy time.

---

## Billing edge Errors alarm (W8-P8)

| Resource | Name pattern |
|----------|----------------|
| Alarm | `StreamMyCourse-BillingEdge-{env}-Errors` |
| Metric | `AWS/Lambda` · `Errors` · function `StreamMyCourse-BillingEdge-{env}` |
| Threshold | **Sum ≥ 1** over **86400 s** (1 day), 1 evaluation period |
| Action | `StreamMyCourse-BillingFulfillment-Alerts-{env}` |

### Triage steps

1. Open log group `/aws/lambda/StreamMyCourse-BillingEdge-{env}` for the alarm window.
2. Filter by **request ID** and route:
   - `POST /billing/cancel-subscription` — see [Provider cancel failed](#provider-cancel-failed-502)
   - `POST /webhooks/payments/paytabs` — see [IPN signature failures](#ipn-signature-failures-draft)
   - `POST /billing/checkout-session` — catalog precheck / `billing_unconfigured`
3. **Mock era:** most edge errors are config, catalog invoke, or test traffic — not PayTabs outages.

---

## Student cancel (immediate provider cancel)

**Design (WS8):** No period-end scheduler. Cancel stops **renewals at the provider** as soon as the student cancel succeeds in RDS.

**Flow:**

1. Student **`POST /billing/cancel-subscription`** (Cognito `sub` only).
2. Catalog internal **`billing.cancel_at_period_end`** → RDS: `status=canceled`, `cancel_at_period_end=true`, period unchanged.
3. Billing edge **`cancel_agreement(provider_subscription_id)`** — mock no-op while mock is on; real HTTP at WS9.
4. **200** only if RDS **and** provider cancel succeed.

**Access:** Lesson access remains until **`current_period_end`** (canceled-in-period is still granting). Checkout returns **409 `already_subscribed`** until period ends.

---

## Provider cancel failed (502)

**Symptom:** Student receives **502** with code **`provider_cancel_failed`** — *“Unable to cancel subscription with payment provider.”*

**Meaning:** RDS cancel-at-period-end **already committed**. PayTabs **`cancel_agreement`** failed (network, 4xx/5xx, bad agreement id). Renewals might still be possible at PayTabs until cancel succeeds.

| Actor | Action |
|-------|--------|
| **Student** | Retry **`POST /billing/cancel-subscription`** after a short wait. Subscription UI should show canceled-in-period if RDS step succeeded. |
| **Ops** | 1) Confirm RDS row: `canceled`, `cancel_at_period_end=true`, future `current_period_end`. 2) Logs: `provider_cancel_agreement_failed` with `user_sub` and `provider_subscription_id` (no secrets). 3) At WS9: verify agreement canceled in PayTabs dashboard; re-run cancel or manual agreement cancel per PayTabs support if retries fail. |

**Not** fixed by reactivate — route removed (see below).

---

## IPN signature failures (draft)

**Symptom:** PayTabs IPN **`POST /webhooks/payments/paytabs`** returns **401** `invalid_signature`.

**Verification (live / WS9):**

- Header **`Signature`**: HMAC-SHA256 of **raw body** with **Server Key** (from Secrets Manager `streammycourse/paytabs/{env}` — compare in console, do not paste keys into tickets).
- Body must be unmodified (no API Gateway transformation of the payload).
- Wrong env: **400** `environment_mismatch` — different from signature failure.

**Mock (WS8):**

- Adapter accepts header **`X-Mock-Signature: test`** when `PAYTABS_USE_MOCK=true`.
- Fixture IPNs in tests only; production traffic should not rely on mock signature in WS9.

**Ops checklist (draft):** dashboard IPN URL matches API stage; server key rotated in SM and redeployed; clock/skew N/A for HMAC; repeated 401s — capture PayTabs delivery logs and one redacted request id from edge logs.

---

## No reactivate — wait, then new subscribe

**Removed in WS8:** `POST /billing/reactivate-subscription`, catalog `billing.reactivate*`, and `reactivation_required` checkout gate.

| Student state | Cancel button | Checkout |
|---------------|---------------|----------|
| Active / past_due in period | Cancel → provider + RDS | **409 `already_subscribed`** |
| Canceled-in-period (future `current_period_end`) | No (already canceled) | **409 `already_subscribed`** |
| Period ended (no granting access) | N/A | **200** — new HPP / subscribe |

**Support script:** “Cancel stops renewal; you keep access until {date}. To subscribe again, wait until after that date and use Subscribe — we can’t undo cancel.”

---

## Related alarms (cost only)

Monthly **billing cost** alarm lives in [`billing-alarm.yaml`](../templates/billing-alarm.yaml) — not subscription fulfillment. Do not confuse with DLQ/edge SNS above.

---

## WS9 handoff

Before `PAYTABS_USE_MOCK=false`: confirm SNS email subscriptions, run live cancel + IPN smoke, and extend IPN section with PayTabs dashboard screenshots and escalation contacts.
