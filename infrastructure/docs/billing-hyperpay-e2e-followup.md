# HyperPay E2E — follow-up after flow works

Track cleanup once pay → HyperPay → webhook or checkout-status → RDS `paid` is verified in prod.

## Product / flow

- [ ] Confirm browser COPYandPAY path (widget + 3DS) creates portal **Success** with real `v2|prod|{userSub}|bundle|{purchaseId}` cart ids.
- [ ] Confirm `GET /billing/purchases` shows **paid** for that purchase without manual RDS fixes.
- [ ] Decide whether to keep **checkout-status** poll long-term or rely on webhooks only after HyperPay delivery is stable.

## Logging (added for debug)

- [ ] **Tighten** billing edge logs after E2E is green: keep correlation fields (`requestId`, `purchase_id`, `checkout_id_prefix`, `oppwa_result_code`, `status`); drop noise if any.
- [ ] **Secure logging review:** no card data, no webhook ciphertext, no full `user_sub` in new lines if we add more; align with `infrastructure/docs/billing-ops-runbook.md`.
- [ ] Document CloudWatch filter cheat sheet in runbook (checkout_session_*, checkout_status_poll, webhook_enqueued, billing_fulfillment processed).

## Security / hardening (put back after debug)

- [ ] Remove **`VITE_HYPERPAY_SKIP_WIDGET_INTEGRITY`** from student builds; rely on OPPWA `integrity` on `paymentWidgets.js` only.
- [ ] Keep strict HyperPay webhook validation (401 decrypt fail, no fail-open).
- [ ] Remove or gate **operator-only** scripts (`scripts/hyperpay_eu_test_s2s_smoke.py`, widget e2e) from default workflows; do not run against prod except controlled ops.
- [ ] Re-review CORS, CSP, and billing edge auth on manage routes.

## Tests / CI

- [ ] Keep `tests/integration/test_billing_hyperpay_full_flow.py` on a student **without** paid bundle (`student-test@noreply.local` pattern).
- [ ] Optional: unit assertion that checkout-status success path logs `enqueued=true` (caplog) if we want regression guard.

## Ops

- [ ] Update `ImplementationHistory.md` when E2E is proven (date + evidence: portal + purchase id).
- [ ] Reply to HyperPay / close test-entity checklist in `billing-ops-runbook.md` if needed.
