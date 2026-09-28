-- 020_assignments.sql
--
-- RS-13: module-scoped assignments, file submissions, rubric grading.
-- Idempotent where practical (IF NOT EXISTS). Pre-launch: no backfill.

CREATE TABLE IF NOT EXISTS assignments (
    id                          UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id                   UUID         NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    module_id                   UUID         NOT NULL,
    title                       VARCHAR(200) NOT NULL,
    status                      VARCHAR(20)  NOT NULL DEFAULT 'draft',
    pass_percent                INTEGER      NOT NULL DEFAULT 70,
    counts_toward_certificate   BOOLEAN      NOT NULL DEFAULT FALSE,
    instructions_mode           VARCHAR(20)  NOT NULL DEFAULT 'plain',
    instructions_text           TEXT         NOT NULL DEFAULT '',
    instructions_html           TEXT         NOT NULL DEFAULT '',
    instructions_image_key      VARCHAR(500) NOT NULL DEFAULT '',
    instructions_image_ready    BOOLEAN      NOT NULL DEFAULT FALSE,
    rubric_mode                 VARCHAR(20)  NOT NULL DEFAULT 'plain',
    rubric_text                 TEXT         NOT NULL DEFAULT '',
    rubric_html                 TEXT         NOT NULL DEFAULT '',
    rubric_image_key            VARCHAR(500) NOT NULL DEFAULT '',
    rubric_image_ready          BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT assignments_status_check CHECK (status IN ('draft', 'published')),
    CONSTRAINT assignments_pass_percent_check CHECK (pass_percent >= 1 AND pass_percent <= 100),
    CONSTRAINT assignments_instructions_mode_check CHECK (
        instructions_mode IN ('plain', 'rich', 'image')
    ),
    CONSTRAINT assignments_rubric_mode_check CHECK (
        rubric_mode IN ('plain', 'rich', 'image')
    ),
    FOREIGN KEY (course_id, module_id)
        REFERENCES course_modules (course_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_assignments_course
    ON assignments (course_id);

CREATE INDEX IF NOT EXISTS idx_assignments_course_module
    ON assignments (course_id, module_id);

CREATE TABLE IF NOT EXISTS assignment_criteria (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    assignment_id   UUID         NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    label           VARCHAR(120) NOT NULL,
    max_points      INTEGER      NOT NULL,
    sort_order      INTEGER      NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT assignment_criteria_max_points_check CHECK (max_points >= 1 AND max_points <= 100)
);

CREATE INDEX IF NOT EXISTS idx_assignment_criteria_assignment
    ON assignment_criteria (assignment_id, sort_order);

CREATE TABLE IF NOT EXISTS assignment_submissions (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    assignment_id   UUID         NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    course_id       UUID         NOT NULL,
    user_sub        VARCHAR(255) NOT NULL,
    status          VARCHAR(20)  NOT NULL DEFAULT 'draft',
    note            TEXT         NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    submitted_at    TIMESTAMPTZ,
    CONSTRAINT assignment_submissions_status_check CHECK (
        status IN ('draft', 'submitted', 'graded')
    )
);

CREATE INDEX IF NOT EXISTS idx_assignment_submissions_assignment_user
    ON assignment_submissions (assignment_id, user_sub);

-- One open draft submission per student per assignment.
CREATE UNIQUE INDEX IF NOT EXISTS assignment_submissions_one_draft_per_user
    ON assignment_submissions (assignment_id, user_sub)
    WHERE status = 'draft';

CREATE TABLE IF NOT EXISTS assignment_submission_files (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id   UUID         NOT NULL REFERENCES assignment_submissions(id) ON DELETE CASCADE,
    assignment_id   UUID         NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    course_id       UUID         NOT NULL,
    title           VARCHAR(255) NOT NULL,
    file_type       VARCHAR(20)  NOT NULL,
    object_key      VARCHAR(500) NOT NULL DEFAULT '',
    content_type    VARCHAR(100) NOT NULL DEFAULT '',
    byte_size       BIGINT       NOT NULL DEFAULT 0,
    status          VARCHAR(20)  NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT assignment_submission_files_status_check CHECK (
        status IN ('pending', 'ready')
    ),
    CONSTRAINT assignment_submission_files_byte_size_nonneg CHECK (byte_size >= 0),
    CONSTRAINT assignment_submission_files_type_check CHECK (
        file_type IN ('pdf', 'csv', 'xlsx', 'docx', 'sav')
    )
);

CREATE INDEX IF NOT EXISTS idx_assignment_submission_files_submission
    ON assignment_submission_files (submission_id);

CREATE TABLE IF NOT EXISTS assignment_grades (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id   UUID         NOT NULL UNIQUE REFERENCES assignment_submissions(id) ON DELETE CASCADE,
    assignment_id   UUID         NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    course_id       UUID         NOT NULL,
    score_percent   INTEGER      NOT NULL,
    pass_percent    INTEGER      NOT NULL,
    passed          BOOLEAN      NOT NULL,
    feedback        TEXT         NOT NULL,
    graded_by       VARCHAR(255) NOT NULL,
    graded_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT assignment_grades_score_percent_check CHECK (
        score_percent >= 0 AND score_percent <= 100
    ),
    CONSTRAINT assignment_grades_pass_percent_check CHECK (
        pass_percent >= 1 AND pass_percent <= 100
    )
);

CREATE TABLE IF NOT EXISTS assignment_grade_scores (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    grade_id        UUID         NOT NULL REFERENCES assignment_grades(id) ON DELETE CASCADE,
    criterion_id    UUID         NOT NULL REFERENCES assignment_criteria(id) ON DELETE CASCADE,
    points          INTEGER      NOT NULL,
    CONSTRAINT assignment_grade_scores_points_nonneg CHECK (points >= 0),
    CONSTRAINT assignment_grade_scores_unique UNIQUE (grade_id, criterion_id)
);

CREATE INDEX IF NOT EXISTS idx_assignment_grade_scores_grade
    ON assignment_grade_scores (grade_id);
