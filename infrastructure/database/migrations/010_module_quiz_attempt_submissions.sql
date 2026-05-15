-- 010_module_quiz_attempt_submissions.sql
--
-- QB-H slice 1: persisted student answers + score totals per submitted attempt.
-- Idempotent: CREATE TABLE IF NOT EXISTS only (mirror 009).

CREATE TABLE IF NOT EXISTS module_quiz_attempt_submissions (
    attempt_id       UUID PRIMARY KEY
        REFERENCES module_quiz_attempts(id) ON DELETE CASCADE,
    answers_json     JSONB NOT NULL,
    correct_count    INTEGER NOT NULL,
    total_count      INTEGER NOT NULL,
    submitted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (jsonb_typeof(answers_json) = 'object'),
    CHECK (total_count >= 1),
    CHECK (correct_count >= 0),
    CHECK (correct_count <= total_count)
);
