-- 018_module_quiz_pass_percent.sql
--
-- RS-8: per-module quiz pass threshold (percent) for sequential gating.
-- Idempotent: ADD COLUMN IF NOT EXISTS; constraint replaced via DROP IF EXISTS.

ALTER TABLE module_quizzes
    ADD COLUMN IF NOT EXISTS pass_percent INTEGER NOT NULL DEFAULT 70;

ALTER TABLE module_quizzes
    DROP CONSTRAINT IF EXISTS module_quizzes_pass_percent_range;

ALTER TABLE module_quizzes
    ADD CONSTRAINT module_quizzes_pass_percent_range
    CHECK (pass_percent >= 1 AND pass_percent <= 100);
