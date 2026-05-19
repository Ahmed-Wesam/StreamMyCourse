-- 011_billing_subscription.sql
--
-- WS1 billing: subscription plans, teacher merchant profile, user subscriptions,
-- and payment webhook dedupe. Provider-neutral columns (v1 default paytabs).
-- Idempotent: CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS,
-- INSERT ... ON CONFLICT DO NOTHING for plan seeds.

-- -------------------------- subscription_plans --------------------------
CREATE TABLE IF NOT EXISTS subscription_plans (
    id                 UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    environment        VARCHAR(32)  NOT NULL,
    plan_key           VARCHAR(64)  NOT NULL,
    currency           VARCHAR(3)   NOT NULL DEFAULT 'JOD',
    -- amount_minor: fils (1 JOD = 1000 fils). Seed 50000 = 50.000 JOD / month.
    amount_minor       INTEGER      NOT NULL,
    billing_interval   VARCHAR(16)  NOT NULL DEFAULT 'monthly',
    provider           VARCHAR(32)  NOT NULL DEFAULT 'paytabs',
    provider_plan_ref  VARCHAR(255),
    active             BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (environment, plan_key),
    UNIQUE (id, environment),
    CONSTRAINT subscription_plans_amount_minor_positive CHECK (amount_minor > 0)
);

CREATE INDEX IF NOT EXISTS idx_subscription_plans_environment
    ON subscription_plans (environment);

-- -------------------------- teacher_merchant_accounts --------------------------
-- One merchant profile per deployment environment (no PayTabs Server Key in RDS).
CREATE TABLE IF NOT EXISTS teacher_merchant_accounts (
    environment           VARCHAR(32)  PRIMARY KEY,
    teacher_sub           VARCHAR(255) NOT NULL,
    provider              VARCHAR(32)  NOT NULL DEFAULT 'paytabs',
    provider_profile_id   VARCHAR(255),
    payout_ready          BOOLEAN      NOT NULL DEFAULT FALSE,
    payout_ready_at       TIMESTAMPTZ,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- -------------------------- user_subscriptions --------------------------
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id                        UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_sub                  VARCHAR(255) NOT NULL REFERENCES users(user_sub),
    environment               VARCHAR(32)  NOT NULL,
    plan_id                   UUID         NOT NULL,
    provider                  VARCHAR(32)  NOT NULL,
    provider_subscription_id  VARCHAR(255),
    provider_customer_ref     VARCHAR(255),
    status                    VARCHAR(32)  NOT NULL,
    current_period_start      TIMESTAMPTZ,
    current_period_end        TIMESTAMPTZ,
    cancel_at_period_end      BOOLEAN      NOT NULL DEFAULT FALSE,
    canceled_at               TIMESTAMPTZ,
    created_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT user_subscriptions_status_valid
        CHECK (status IN ('active', 'past_due', 'canceled', 'expired', 'incomplete')),
    CONSTRAINT user_subscriptions_plan_environment_fkey
        FOREIGN KEY (plan_id, environment) REFERENCES subscription_plans (id, environment)
);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_env
    ON user_subscriptions (user_sub, environment);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_status_period_end
    ON user_subscriptions (status, current_period_end);

-- Partial unique: at most one granting subscription per user per environment.
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_subscriptions_one_granting_per_user_env
    ON user_subscriptions (user_sub, environment)
    WHERE status IN ('active', 'past_due', 'incomplete');

CREATE UNIQUE INDEX IF NOT EXISTS uq_user_subscriptions_provider_subscription_id
    ON user_subscriptions (provider, provider_subscription_id)
    WHERE provider_subscription_id IS NOT NULL;

-- -------------------------- payment_webhook_events --------------------------
CREATE TABLE IF NOT EXISTS payment_webhook_events (
    id                 UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    environment        VARCHAR(32)  NOT NULL,
    provider           VARCHAR(32)  NOT NULL,
    provider_event_id  VARCHAR(255) NOT NULL,
    event_type         VARCHAR(64)  NOT NULL,
    received_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    processed_at       TIMESTAMPTZ,
    payload_digest     VARCHAR(128),
    UNIQUE (provider, provider_event_id)
);

CREATE INDEX IF NOT EXISTS idx_payment_webhook_events_environment_received
    ON payment_webhook_events (environment, received_at);

-- Seed default monthly JOD plans (dev + prod). Fixed UUIDs keep plan_id stable on re-apply.
INSERT INTO subscription_plans (
    id,
    environment,
    plan_key,
    currency,
    amount_minor,
    billing_interval,
    provider,
    active
) VALUES
    (
        'a0000000-0000-4000-8000-000000000011'::uuid,
        'dev',
        'monthly_all_access',
        'JOD',
        50000,
        'monthly',
        'paytabs',
        TRUE
    ),
    (
        'a0000000-0000-4000-8000-000000000012'::uuid,
        'prod',
        'monthly_all_access',
        'JOD',
        50000,
        'monthly',
        'paytabs',
        TRUE
    )
ON CONFLICT (environment, plan_key) DO NOTHING;
