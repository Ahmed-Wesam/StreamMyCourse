-- 016_user_profile_fields.sql
--
-- RS-6: extended student/instructor profile fields on users (nullable).
-- Idempotent: ADD COLUMN IF NOT EXISTS is safe to re-run on every deploy.

ALTER TABLE users ADD COLUMN IF NOT EXISTS given_name VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS family_name VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS profession VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS institution VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS research_interests TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS privacy_accepted_at TIMESTAMPTZ;
