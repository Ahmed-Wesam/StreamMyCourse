-- 009_module_quiz_attempts.sql
--
-- QB-G slice 1: per-binding quiz attempts with persisted presentation shuffle.
-- Idempotent: CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS module_quiz_attempts (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    binding_id              UUID NOT NULL
        REFERENCES student_module_quiz_bindings(id) ON DELETE CASCADE,
    attempt_number          INTEGER NOT NULL,
    status                  VARCHAR(32) NOT NULL,
    shuffled_question_order JSONB NOT NULL,
    shuffled_choice_orders  JSONB NOT NULL,
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at            TIMESTAMPTZ,
    UNIQUE (binding_id, attempt_number),
    CHECK (attempt_number >= 1),
    CHECK (status IN ('in_progress', 'submitted')),
    CHECK (jsonb_typeof(shuffled_question_order) = 'array'),
    CHECK (jsonb_typeof(shuffled_choice_orders) = 'object')
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_module_quiz_attempts_one_in_progress
    ON module_quiz_attempts (binding_id)
    WHERE status = 'in_progress';
