-- 002_add_course_modules.sql
--
-- Upgrade path for databases created from an earlier 001 that did not include
-- course modules. This migration is intended for in-place upgrade (no wipe).
--
-- Summary:
-- - Create course_modules (one default module per existing course).
-- - Add lessons.module_id, backfill it to the default module, then enforce NOT NULL.
-- - Replace lessons ordering uniqueness: (course_id, lesson_order) -> (course_id, module_id, lesson_order).
-- - Add composite FK lessons(course_id, module_id) -> course_modules(course_id, id).
--
-- NOTE: The RDS Query Lambda currently executes one SQL statement per invoke.
-- Apply this file by running the statements sequentially (in order).
--
-- 1) Create course_modules
CREATE TABLE IF NOT EXISTS course_modules (
    id             UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id      UUID         NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title          VARCHAR(255) NOT NULL,
    description    TEXT         NOT NULL DEFAULT '',
    module_order   INTEGER      NOT NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS course_modules_course_id_module_order_key
    ON course_modules (course_id, module_order);

CREATE UNIQUE INDEX IF NOT EXISTS course_modules_course_id_id_key
    ON course_modules (course_id, id);

CREATE INDEX IF NOT EXISTS idx_course_modules_course_order
    ON course_modules (course_id, module_order);

-- 2) Add lessons.module_id as nullable first
ALTER TABLE lessons ADD COLUMN IF NOT EXISTS module_id UUID;

-- 3) Backfill default module per course (module_order 0)
INSERT INTO course_modules (course_id, title, description, module_order)
SELECT c.id, 'Overview', '', 0
FROM courses c
WHERE NOT EXISTS (
    SELECT 1 FROM course_modules m WHERE m.course_id = c.id AND m.module_order = 0
);

-- 4) Backfill lessons.module_id to default module for that course
UPDATE lessons l
SET module_id = m.id
FROM course_modules m
WHERE l.course_id = m.course_id
  AND m.module_order = 0
  AND (l.module_id IS NULL);

-- 5) Enforce module_id presence
ALTER TABLE lessons ALTER COLUMN module_id SET NOT NULL;

-- 6) Replace uniqueness/indexing for lesson ordering
ALTER TABLE lessons DROP CONSTRAINT IF EXISTS lessons_course_id_lesson_order_key;
DROP INDEX IF EXISTS idx_lessons_course_order;

CREATE UNIQUE INDEX IF NOT EXISTS lessons_course_id_module_id_lesson_order_key
    ON lessons (course_id, module_id, lesson_order);

CREATE INDEX IF NOT EXISTS idx_lessons_course_module_order
    ON lessons (course_id, module_id, lesson_order);

-- 7) Add composite FK (cannot be expressed with IF NOT EXISTS)
ALTER TABLE lessons
    ADD CONSTRAINT lessons_course_id_module_id_fkey
    FOREIGN KEY (course_id, module_id)
    REFERENCES course_modules (course_id, id)
    ON DELETE CASCADE;

