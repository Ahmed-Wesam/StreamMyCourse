-- 006_question_banks_module_quizzes.sql
--
-- QB-A: module → quiz → bank (see plans/question-banks-requirements.md §3,
-- plans/question-banks-mega-plan.md QB-A). Course-scoped banks; at most one
-- quiz per module; at most one module_quizzes row per non-null question_bank_id
-- per course; optional question_bank_id until linked; served_count_n NULL
-- until publish (QB-E / QB-C).
--
-- Idempotent: CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS.

-- -------------------------- question_banks --------------------------
CREATE TABLE IF NOT EXISTS question_banks (
    id             UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id      UUID         NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    name           VARCHAR(80),
    status         VARCHAR(20)  NOT NULL DEFAULT 'DRAFT',
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT question_banks_status_valid CHECK (status IN ('DRAFT', 'PUBLISHED')),
    CONSTRAINT question_banks_name_non_empty
        CHECK (name IS NULL OR (length(btrim(name)) BETWEEN 1 AND 80))
);

-- Composite key target so module_quizzes can enforce same-course bank attachment.
CREATE UNIQUE INDEX IF NOT EXISTS uq_question_banks_course_id_id
    ON question_banks (course_id, id);

CREATE INDEX IF NOT EXISTS idx_question_banks_course_id ON question_banks (course_id);

-- -------------------------- module_quizzes --------------------------
CREATE TABLE IF NOT EXISTS module_quizzes (
    id                 UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id          UUID         NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    module_id          UUID         NOT NULL,
    question_bank_id   UUID,
    served_count_n     INTEGER,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT module_quizzes_served_count_n_positive
        CHECK (served_count_n IS NULL OR served_count_n >= 1),
    UNIQUE (module_id),
    FOREIGN KEY (course_id, module_id) REFERENCES course_modules (course_id, id) ON DELETE CASCADE,
    FOREIGN KEY (course_id, question_bank_id) REFERENCES question_banks (course_id, id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_module_quizzes_course_id ON module_quizzes (course_id);
CREATE INDEX IF NOT EXISTS idx_module_quizzes_question_bank_id ON module_quizzes (question_bank_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_module_quizzes_course_question_bank
    ON module_quizzes (course_id, question_bank_id)
    WHERE question_bank_id IS NOT NULL;
