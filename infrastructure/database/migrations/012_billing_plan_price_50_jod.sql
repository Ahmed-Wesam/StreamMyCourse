-- 012_billing_plan_price_50_jod.sql
--
-- WS6 go-live price: 50 JOD / month for monthly_all_access (dev + prod).
-- amount_minor uses fils (1 JOD = 1000 fils) → 50000 fils = 50.000 JOD.
-- Idempotent: UPDATE is safe to re-run (no-op when rows already at 50000).

UPDATE subscription_plans
SET
    amount_minor = 50000,
    updated_at   = NOW()
WHERE plan_key = 'monthly_all_access';
