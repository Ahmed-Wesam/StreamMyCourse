-- 002_lesson_progress.sql
-- Per-user lesson completion and resume position (RDS only).

CREATE TABLE IF NOT EXISTS lesson_progress (
    user_sub          VARCHAR(255) NOT NULL REFERENCES users(user_sub) ON DELETE CASCADE,
    lesson_id         UUID NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    course_id         UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    completed         BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at    TIMESTAMPTZ,
    last_position_sec INTEGER NOT NULL DEFAULT 0,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_sub, lesson_id),
    CONSTRAINT chk_lesson_progress_position_nonneg CHECK (last_position_sec >= 0)
);

CREATE INDEX IF NOT EXISTS idx_lesson_progress_course_user
    ON lesson_progress (course_id, user_sub);
