-- 001_initial_schema.sql
--
-- StreamMyCourse RDS PostgreSQL initial schema (matches the domain models under
-- infrastructure/lambda/catalog/services/course_management/models.py).
--
-- Column naming: snake_case in SQL; the Python adapter (rds_repo.py) maps to the
-- camelCase fields on the domain objects (createdAt, thumbnailKey, etc.).
-- Timestamps use TIMESTAMPTZ for unambiguous UTC semantics.
-- courses.created_by is NOT NULL with no default; a CHECK constraint enforces
-- non-blank values (btrim(created_by) <> '').

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -------------------------- Users --------------------------
-- user_sub is the Cognito sub (opaque string) and is the primary key for
-- joins (enrollments.user_sub).
CREATE TABLE IF NOT EXISTS users (
    user_sub     VARCHAR(255) PRIMARY KEY,
    email        VARCHAR(255) NOT NULL DEFAULT '',
    role         VARCHAR(20)  NOT NULL DEFAULT 'student',
    cognito_sub  VARCHAR(255) NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- -------------------------- Courses --------------------------
CREATE TABLE IF NOT EXISTS courses (
    id             UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    title          VARCHAR(255) NOT NULL,
    description    TEXT         NOT NULL DEFAULT '',
    status         VARCHAR(20)  NOT NULL DEFAULT 'DRAFT',
    created_by     VARCHAR(255) NOT NULL,
    thumbnail_key  VARCHAR(500) NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT courses_created_by_not_blank CHECK (btrim(created_by) <> '')
);

CREATE INDEX IF NOT EXISTS idx_courses_status ON courses(status);
CREATE INDEX IF NOT EXISTS idx_courses_created_by ON courses(created_by);

-- -------------------------- Course modules --------------------------
-- Logical sections within a course. Every lesson belongs to exactly one module.
CREATE TABLE IF NOT EXISTS course_modules (
    id             UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id      UUID         NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title          VARCHAR(255) NOT NULL,
    description    TEXT         NOT NULL DEFAULT '',
    module_order   INTEGER      NOT NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (course_id, module_order),
    UNIQUE (course_id, id)
);

CREATE INDEX IF NOT EXISTS idx_course_modules_course_order
    ON course_modules (course_id, module_order);

-- -------------------------- Lessons --------------------------
-- ON DELETE CASCADE mirrors CourseCatalogRepository.delete_course_and_lessons
-- (single batch delete of course row + all lesson rows).
-- ON DELETE CASCADE from course_modules: deleting a module removes its lessons.
-- UNIQUE (course_id, module_id, lesson_order) prevents accidental duplicate display positions
-- during reorder operations within a module.
-- Composite FK guarantees lessons.module_id refers to a module_row for same course_id.
CREATE TABLE IF NOT EXISTS lessons (
    id             UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id      UUID         NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    module_id      UUID         NOT NULL,
    title          VARCHAR(255) NOT NULL,
    lesson_order   INTEGER      NOT NULL,
    video_key      VARCHAR(500) NOT NULL DEFAULT '',
    video_status   VARCHAR(20)  NOT NULL DEFAULT 'pending',
    thumbnail_key  VARCHAR(500) NOT NULL DEFAULT '',
    duration       INTEGER      NOT NULL DEFAULT 0,
    UNIQUE (course_id, module_id, lesson_order),
    UNIQUE (course_id, id),
    FOREIGN KEY (course_id, module_id) REFERENCES course_modules (course_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lessons_course_module_order
    ON lessons (course_id, module_id, lesson_order);

-- -------------------------- Enrollments --------------------------
-- The FK to users.user_sub means a profile row must exist before an enrollment.
-- The auth service already calls get_or_create_profile() on every authenticated
-- request, so the profile row is guaranteed present by the time any user tries
-- to enroll. The migration script inserts users before enrollments.
CREATE TABLE IF NOT EXISTS enrollments (
    user_sub     VARCHAR(255) NOT NULL REFERENCES users(user_sub),
    course_id    UUID         NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    enrolled_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    source       VARCHAR(50)  NOT NULL DEFAULT 'self_service',
    PRIMARY KEY (user_sub, course_id)
);

-- Reverse lookup for future "who is enrolled in course X?" (teacher dashboards).
-- Cheap to add now; no reason to defer.
CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_id);

-- -------------------------- Lesson Progress --------------------------
-- Tracks student progress through individual lessons. The composite
-- primary key (user_sub, lesson_id) ensures one progress record per
-- user per lesson. A composite FK enforces that the (course_id, lesson_id)
-- pair is valid for the same course. ON DELETE CASCADE mirrors the enrollment
-- behavior when users or courses/lessons are removed.
CREATE TABLE IF NOT EXISTS lesson_progress (
    user_sub          VARCHAR(255) NOT NULL REFERENCES users(user_sub) ON DELETE CASCADE,
    lesson_id         UUID NOT NULL,
    course_id         UUID NOT NULL,
    completed         BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at      TIMESTAMPTZ,
    last_position_sec INTEGER NOT NULL DEFAULT 0,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_sub, lesson_id),
    CONSTRAINT chk_lesson_progress_position_nonneg CHECK (last_position_sec >= 0),
    -- Named explicitly so migration 003 can drop and re-add this FK by a stable
    -- name (otherwise PostgreSQL auto-generates lesson_progress_course_id_lesson_id_fkey
    -- on fresh DBs, leaving a redundant FK after 003 runs).
    CONSTRAINT lesson_progress_course_lesson_fkey FOREIGN KEY (course_id, lesson_id) REFERENCES lessons (course_id, id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
);

-- Index for efficient "get all progress for user in course" queries
-- used by the course progress API endpoint.
CREATE INDEX IF NOT EXISTS idx_lesson_progress_course_user
    ON lesson_progress (course_id, user_sub);
