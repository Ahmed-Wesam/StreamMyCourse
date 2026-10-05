-- 023_rs16_learning_features.sql
--
-- RS-16: lesson transcripts, learning-activity days for streaks, and
-- account learning preferences. Idempotent (IF NOT EXISTS).
-- research_interests (free text) is unchanged; research_interest_tags stores
-- the five Settings allowlist keys only.

ALTER TABLE lessons ADD COLUMN IF NOT EXISTS transcript TEXT;

CREATE TABLE IF NOT EXISTS learning_activity_days (
    user_sub VARCHAR(255) NOT NULL REFERENCES users(user_sub) ON DELETE CASCADE,
    day      DATE         NOT NULL,
    PRIMARY KEY (user_sub, day)
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS pref_autoplay_next BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS pref_auto_mark_complete BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS pref_progress_celebrations BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS research_interest_tags TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;
