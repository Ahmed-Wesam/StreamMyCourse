# RS-5 Slice D handoff (billing_edge → catalog purchases checkout)

Slice C implemented the catalog side. **Slice D** wires **billing_edge** to one-time purchase checkout, PayTabs sale HPP, IPN, and fulfillment.

## Internal invoke: `billing.checkout`

Route when the event includes **`productType`** (`course` | `bundle`):

| Field | Required | Notes |
|-------|----------|--------|
| `internal` | yes | `"billing.checkout"` |
| `userSub` | yes | Cognito sub |
| `productType` | yes | `"course"` or `"bundle"` |
| `courseId` | when `productType=course` | UUID string |

### Success (precheck passed, pending row reserved)

```json
{
  "blockReason": null,
  "product": {
    "amount_minor": 9900,
    "currency": "USD",
    "course_id": "…",
    "purchase_id": "…"
  }
}
```

Bundle response uses `product_type: "bundle"` instead of `course_id`.

### Blocks (edge maps to HTTP 409)

| `blockReason` | HTTP `code` |
|---------------|-------------|
| `already_owned` | `already_owned` |
| `checkout_in_progress` | `checkout_in_progress` |

## Internal invoke: `billing.rollback_checkout`

Same `productType` / `courseId` fields. Deletes matching **`pending`** purchase rows.

## Edge checkout HTTP

`POST /billing/checkout-session` body:

```json
{ "productType": "course", "courseId": "uuid" }
```

or `{ "productType": "bundle" }`.

## PayTabs HPP (`create_sale_session`)

- `cart_id`: `v2|{env}|{user_sub}|course|{courseId}|{purchaseId}` or `v2|{env}|{user_sub}|bundle|{purchaseId}`
- `cart_amount`: `amount_minor / 100`, `cart_currency`: `USD`
- `return`: `BILLING_RETURN_SUCCESS_URL`
- `callback`: `BILLING_IPN_CALLBACK_URL` (IPN webhook URL, not cancel URL)

## Mock IPN samples (integration / manual POST)

Use header `X-Mock-Signature: test` when `PAYTABS_USE_MOCK=true`.

**Purchase paid (course):**

```json
{
  "tran_ref": "MOCK-ACT-001",
  "tran_type": "Sale",
  "payment_result": "A",
  "cart_id": "v2|dev|{user_sub}|course|{courseId}|{purchaseId}",
  "cart_amount": 99.0,
  "cart_currency": "USD",
  "transaction_time": "2026-05-18T12:00:00Z"
}
```

**Purchase failed (bundle):**

```json
{
  "tran_ref": "MOCK-DEC-001",
  "tran_type": "Sale",
  "payment_result": "D",
  "cart_id": "v2|dev|{user_sub}|bundle|{purchaseId}",
  "cart_amount": 150.0,
  "cart_currency": "USD"
}
```

**Refund / revoke:**

```json
{
  "tran_ref": "MOCK-REF-001",
  "tran_type": "Refund",
  "payment_result": "A",
  "previous_tran_ref": "MOCK-ACT-001",
  "cart_id": "v2|dev|{user_sub}|course|{courseId}|{purchaseId}",
  "cart_amount": 99.0,
  "cart_currency": "USD"
}
```

Domain events: `purchase.paid`, `purchase.failed`, `purchase.revoked`.

## Env vars (billing edge Lambda)

| Variable | Purpose |
|----------|---------|
| `DEPLOYMENT_ENVIRONMENT` | `dev` / `prod` |
| `CATALOG_LAMBDA_ARN` | Internal checkout invoke |
| `FULFILLMENT_QUEUE_URL` | SQS after IPN |
| `BILLING_RETURN_SUCCESS_URL` | PayTabs `return` |
| `BILLING_IPN_CALLBACK_URL` | PayTabs `callback` (IPN) |
| `BILLING_RETURN_CANCEL_URL` | Student cancel page (optional; not used on sale HPP) |
| `PAYTABS_*` / `PAYTABS_USE_MOCK` | Provider credentials or mock |

## Still on subscription until aggregation

- `CourseAccessService` in `bootstrap.py` uses `SubscriptionRdsRepository` (not `PurchaseRdsRepository`).
- v1 `cart_id` IPNs still map to subscription domain events until subscription tables are removed.
- `POST /billing/cancel-subscription` unchanged on edge.
