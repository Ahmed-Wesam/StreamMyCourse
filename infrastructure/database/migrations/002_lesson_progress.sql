-- 002_lesson_progress.sql
--
-- StreamMyCourse RDS PostgreSQL lesson progress tracking schema.
-- Stores per-user, per-lesson progress state including completion status
-- and last known video playback position.
--
-- Column naming: snake_case in SQL; Python adapters map to camelCase
-- for API contracts. Timestamps use TIMESTAMPTZ for UTC semantics.

-- -------------------------- Lesson Progress --------------------------
-- Tracks student progress through individual lessons. The composite
-- primary key (user_sub, lesson_id) ensures one progress record per
-- user per lesson. ON DELETE CASCADE mirrors the enrollment behavior
-- when users or courses/lessons are removed.
CREATE TABLE IF NOT EXISTS lesson_progress (
    user_sub          VARCHAR(255) NOT NULL REFERENCES users(user_sub) ON DELETE CASCADE,
    lesson_id         UUID NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    course_id         UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    completed         BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at      TIMESTAMPTZ,
    last_position_sec INTEGER NOT NULL DEFAULT 0,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_sub, lesson_id),
    CONSTRAINT chk_lesson_progress_position_nonneg CHECK (last_position_sec >= 0)
);

-- Index for efficient "get all progress for user in course" queries
-- used by the course progress API endpoint.
CREATE INDEX IF NOT EXISTS idx_lesson_progress_course_user
    ON lesson_progress (course_id, user_sub);
