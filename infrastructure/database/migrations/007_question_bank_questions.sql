-- 007_question_bank_questions.sql
--
-- QB-C / QB-E: MCQ rows scoped by course + question bank (composite FK to
-- question_banks, mirroring module_quizzes). Draft edits vs published corpus.
--
-- Idempotent: CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS questions (
    id                   UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id            UUID         NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    question_bank_id     UUID         NOT NULL,
    status               VARCHAR(20)  NOT NULL DEFAULT 'DRAFT',
    prompt_text          TEXT         NOT NULL DEFAULT '',
    options_json         JSONB        NOT NULL DEFAULT '[]'::jsonb,
    correct_option_key   VARCHAR(128),
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT questions_status_valid CHECK (status IN ('DRAFT', 'PUBLISHED')),
    FOREIGN KEY (course_id, question_bank_id) REFERENCES question_banks (course_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_questions_course_bank
    ON questions (course_id, question_bank_id);

CREATE INDEX IF NOT EXISTS idx_questions_bank_status
    ON questions (question_bank_id, status);
