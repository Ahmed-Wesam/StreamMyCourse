-- 008_student_module_quiz_bindings.sql
--
-- QB-F slice 1: per-student module quiz question bindings (draw order persisted).
-- Idempotent: CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS.

-- Composite FK target for bindings scoped to the same course as module_quizzes.
CREATE UNIQUE INDEX IF NOT EXISTS uq_module_quizzes_course_id_id
    ON module_quizzes (course_id, id);

-- -------------------------- student_module_quiz_bindings --------------------------
CREATE TABLE IF NOT EXISTS student_module_quiz_bindings (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    module_quiz_id  UUID         NOT NULL REFERENCES module_quizzes(id) ON DELETE CASCADE,
    course_id       UUID         NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    user_sub VARCHAR(255) NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (module_quiz_id, user_sub),
    FOREIGN KEY (course_id, module_quiz_id)
        REFERENCES module_quizzes (course_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_student_module_quiz_bindings_course_user
    ON student_module_quiz_bindings (course_id, user_sub);

-- -------------------------- student_module_quiz_binding_questions --------------------------
CREATE TABLE IF NOT EXISTS student_module_quiz_binding_questions (
    binding_id   UUID    NOT NULL
        REFERENCES student_module_quiz_bindings(id) ON DELETE CASCADE,
    position     INTEGER NOT NULL,
    question_id  UUID    NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    PRIMARY KEY (binding_id, position),
    UNIQUE (binding_id, question_id)
);

-- In-place upgrade when 008 was applied with ON DELETE RESTRICT (course delete cleanup).
ALTER TABLE student_module_quiz_binding_questions
    DROP CONSTRAINT IF EXISTS student_module_quiz_binding_questions_question_id_fkey;

ALTER TABLE student_module_quiz_binding_questions
    ADD CONSTRAINT student_module_quiz_binding_questions_question_id_fkey
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE;
