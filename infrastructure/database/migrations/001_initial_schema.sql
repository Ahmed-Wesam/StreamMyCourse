-- 001_initial_schema.sql
--
-- StreamMyCourse RDS PostgreSQL initial schema (matches the domain models under
-- infrastructure/lambda/catalog/services/course_management/models.py and the
-- existing DynamoDB repository contracts).
--
-- Column naming: snake_case in SQL; the Python adapter (rds_repo.py) maps to the
-- camelCase fields on the domain objects (createdAt, thumbnailKey, etc.).
-- Timestamps use TIMESTAMPTZ so UTC semantics from DynamoDB ISO strings survive
-- the migration unambiguously.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -------------------------- Users --------------------------
-- Mirrors the DynamoDB USER#<sub>/METADATA row. user_sub is the Cognito sub
-- (opaque string) and is the primary key for joins (enrollments.user_sub).
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
    created_by     VARCHAR(255) NOT NULL DEFAULT '',
    thumbnail_key  VARCHAR(500) NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_courses_status ON courses(status);
CREATE INDEX IF NOT EXISTS idx_courses_created_by ON courses(created_by);

-- -------------------------- Lessons --------------------------
-- ON DELETE CASCADE mirrors CourseCatalogRepository.delete_course_and_lessons
-- (single batch delete of course row + all lesson rows).
-- UNIQUE (course_id, lesson_order) prevents accidental duplicate display positions
-- during reorder operations.
CREATE TABLE IF NOT EXISTS lessons (
    id             UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id      UUID         NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title          VARCHAR(255) NOT NULL,
    lesson_order   INTEGER      NOT NULL,
    video_key      VARCHAR(500) NOT NULL DEFAULT '',
    video_status   VARCHAR(20)  NOT NULL DEFAULT 'pending',
    thumbnail_key  VARCHAR(500) NOT NULL DEFAULT '',
    duration       INTEGER      NOT NULL DEFAULT 0,
    UNIQUE (course_id, lesson_order)
);

CREATE INDEX IF NOT EXISTS idx_lessons_course_order ON lessons(course_id, lesson_order);

-- -------------------------- Enrollments --------------------------
-- The FK to users.user_sub means a profile row must exist before an enrollment.
-- The auth service already calls get_or_create_profile() on every authenticated
-- request, so the profile row is guaranteed present by the time any user tries
-- to enroll. The migration script inserts users before enrollments.
CREATE TABLE IF NOT EXISTS enrollments (
    user_sub     VARCHAR(255) NOT NULL REFERENCES users(user_sub),
    course_id    UUID         NOT NULL REFERENCES courses(id),
    enrolled_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    source       VARCHAR(50)  NOT NULL DEFAULT 'self_service',
    PRIMARY KEY (user_sub, course_id)
);

-- Reverse lookup for future "who is enrolled in course X?" (teacher dashboards).
-- Cheap to add now; no reason to defer.
CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_id);
