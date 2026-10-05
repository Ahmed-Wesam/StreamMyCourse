-- 024_hyperpay_jod.sql
--
-- HyperPay checkout in JOD: amount_minor is fils (1 JOD = 1000 fils); only whole
-- dinars (multiples of 1000 fils) are allowed for course prices, bundle offers,
-- and purchases. Idempotent: IF EXISTS drops, safe UPDATE/DELETE re-runs.

-- -------------------------- Data cleanup --------------------------
DELETE FROM purchases
WHERE status != 'paid';

DELETE FROM payment_webhook_events
WHERE provider = 'paytabs' OR provider != 'hyperpay';

-- -------------------------- JOD list prices (dev + prod) --------------------------
UPDATE courses
SET price_amount_minor = 50000
WHERE price_amount_minor IS NOT NULL;

UPDATE bundle_offers
SET
    amount_minor = 150000,
    currency       = 'JOD',
    updated_at     = NOW()
WHERE environment IN ('dev', 'prod');

-- Paid rows kept after cleanup: align to canonical whole-JOD fils for HyperPay.
UPDATE purchases
SET
    amount_minor = CASE product_type
        WHEN 'course' THEN 50000
        WHEN 'bundle' THEN 150000
        ELSE amount_minor
    END,
    currency     = 'JOD',
    provider     = 'hyperpay',
    updated_at   = NOW()
WHERE status = 'paid';

-- -------------------------- Defaults --------------------------
ALTER TABLE bundle_offers ALTER COLUMN currency SET DEFAULT 'JOD';
ALTER TABLE purchases ALTER COLUMN currency SET DEFAULT 'JOD';
ALTER TABLE purchases ALTER COLUMN provider SET DEFAULT 'hyperpay';

-- -------------------------- Whole-dinar CHECK constraints --------------------------
ALTER TABLE courses DROP CONSTRAINT IF EXISTS courses_price_amount_minor_non_negative;
ALTER TABLE courses DROP CONSTRAINT IF EXISTS courses_price_amount_minor_whole_jod;
ALTER TABLE courses
    ADD CONSTRAINT courses_price_amount_minor_whole_jod
    CHECK (
        price_amount_minor IS NULL
        OR (price_amount_minor > 0 AND price_amount_minor % 1000 = 0)
    );

ALTER TABLE bundle_offers DROP CONSTRAINT IF EXISTS bundle_offers_amount_minor_positive;
ALTER TABLE bundle_offers DROP CONSTRAINT IF EXISTS bundle_offers_amount_minor_whole_jod;
ALTER TABLE bundle_offers
    ADD CONSTRAINT bundle_offers_amount_minor_whole_jod
    CHECK (amount_minor > 0 AND amount_minor % 1000 = 0);

ALTER TABLE purchases DROP CONSTRAINT IF EXISTS purchases_amount_minor_positive;
ALTER TABLE purchases DROP CONSTRAINT IF EXISTS purchases_amount_minor_whole_jod;
ALTER TABLE purchases
    ADD CONSTRAINT purchases_amount_minor_whole_jod
    CHECK (amount_minor > 0 AND amount_minor % 1000 = 0);

-- -------------------------- Retire PayTabs merchant profile table --------------------------
DROP TABLE IF EXISTS teacher_merchant_accounts;
