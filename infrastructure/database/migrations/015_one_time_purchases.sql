-- 015_one_time_purchases.sql
--
-- RS-5: one-time course + bundle purchases; retire subscription_plans / user_subscriptions.
-- Idempotent: ADD COLUMN IF NOT EXISTS, CREATE TABLE IF NOT EXISTS, DROP TABLE IF EXISTS.

-- -------------------------- courses.price_amount_minor --------------------------
ALTER TABLE courses ADD COLUMN IF NOT EXISTS price_amount_minor INTEGER;

ALTER TABLE courses DROP CONSTRAINT IF EXISTS courses_price_amount_minor_non_negative;
ALTER TABLE courses
    ADD CONSTRAINT courses_price_amount_minor_non_negative
    CHECK (price_amount_minor IS NULL OR price_amount_minor > 0);

-- -------------------------- bundle_offers --------------------------
CREATE TABLE IF NOT EXISTS bundle_offers (
    environment   VARCHAR(32)  PRIMARY KEY,
    amount_minor  INTEGER      NOT NULL,
    currency      VARCHAR(3)   NOT NULL DEFAULT 'USD',
    active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT bundle_offers_amount_minor_positive CHECK (amount_minor > 0)
);

-- -------------------------- purchases --------------------------
CREATE TABLE IF NOT EXISTS purchases (
    id                 UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_sub           VARCHAR(255) NOT NULL REFERENCES users(user_sub),
    environment        VARCHAR(32)  NOT NULL,
    product_type       VARCHAR(16)  NOT NULL,
    course_id          UUID,
    status             VARCHAR(32)  NOT NULL,
    amount_minor       INTEGER      NOT NULL,
    currency           VARCHAR(3)   NOT NULL DEFAULT 'USD',
    provider           VARCHAR(32)  NOT NULL DEFAULT 'paytabs',
    provider_tran_ref  VARCHAR(255),
    cart_id            VARCHAR(255),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT purchases_product_type_valid
        CHECK (product_type IN ('course', 'bundle')),
    CONSTRAINT purchases_status_valid
        CHECK (status IN ('pending', 'paid', 'revoked', 'failed')),
    CONSTRAINT purchases_amount_minor_positive CHECK (amount_minor > 0),
    CONSTRAINT purchases_course_product_requires_course_id
        CHECK (
            (product_type = 'course' AND course_id IS NOT NULL)
            OR (product_type = 'bundle' AND course_id IS NULL)
        ),
    CONSTRAINT purchases_course_id_fkey
        FOREIGN KEY (course_id) REFERENCES courses (id)
);

CREATE INDEX IF NOT EXISTS idx_purchases_user_env
    ON purchases (user_sub, environment);

CREATE INDEX IF NOT EXISTS idx_purchases_provider_tran_ref
    ON purchases (provider, provider_tran_ref)
    WHERE provider_tran_ref IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_purchases_one_paid_course_per_user_course_env
    ON purchases (user_sub, course_id, environment)
    WHERE product_type = 'course' AND status = 'paid';

CREATE UNIQUE INDEX IF NOT EXISTS uq_purchases_one_paid_bundle_per_user_env
    ON purchases (user_sub, environment)
    WHERE product_type = 'bundle' AND status = 'paid';

-- Seed bundle list prices (USD cents: $150.00 = 15000). Safe to re-run.
INSERT INTO bundle_offers (environment, amount_minor, currency, active)
VALUES
    ('dev', 15000, 'USD', TRUE),
    ('prod', 15000, 'USD', TRUE)
ON CONFLICT (environment) DO NOTHING;

-- -------------------------- Retire subscription tables --------------------------
DROP TABLE IF EXISTS user_subscriptions;
DROP TABLE IF EXISTS subscription_plans;
