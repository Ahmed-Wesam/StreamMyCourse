-- 014_rate_limit_counters.sql
--
-- API abuse protection: fixed-window counters per bucket key (RDS adapter).
-- Idempotent: CREATE TABLE IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS rate_limit_counters (
    bucket_key    TEXT PRIMARY KEY,
    window_start  TIMESTAMPTZ NOT NULL,
    count         INT NOT NULL,
    CHECK (count >= 0)
);
