-- 003_progress_course_lesson_fk.sql
--
-- In-place upgrade that closes the cross-course progress invariant gap. Adds
-- the target unique index on lessons (course_id, id) and replaces the legacy
-- single-column FK lesson_progress.lesson_id -> lessons(id) with a composite
-- FK lesson_progress (course_id, lesson_id) -> lessons (course_id, id) ON
-- DELETE CASCADE. Mirrors the canonical schema in 001_initial_schema.sql.
--
-- Apply path: bundled into the schema-applier Lambda alongside 001 and run
-- on every backend deploy from .github/workflows/deploy-backend.yml. The
-- Lambda's _split_sql_statements is a naive `;` split, so every statement
-- here is plain DDL with no DO $$ blocks. Each statement is idempotent so
-- the file is safe to re-run on every CI deploy.
--
-- Drift policy: the operator runs the pre-flight drift SELECT (lesson_progress
-- rows whose (course_id, lesson_id) does not match a lessons row) out-of-band
-- before the first deploy that ships this file. Both dev and prod returned
-- drift_count = 0 at the time this file was authored, so adding the composite
-- FK is safe. If a future drift sneaks in before this migration applies, the
-- ADD CONSTRAINT below will fail loudly and roll back the whole apply.

-- 1) FK target uniqueness. CREATE UNIQUE INDEX IF NOT EXISTS is natively
--    idempotent and is sufficient to back a composite FOREIGN KEY in
--    PostgreSQL (matches the style used for course_modules in 002).
CREATE UNIQUE INDEX IF NOT EXISTS lessons_course_id_id_key
    ON lessons (course_id, id);

-- 2) Drop the legacy single-column FK on lesson_progress.lesson_id. The
--    PostgreSQL-generated default name for the inline `lesson_id UUID NOT
--    NULL REFERENCES lessons(id)` declaration is deterministic
--    (`<table>_<column>_fkey`); confirmed on dev and prod before this file
--    was committed. IF EXISTS makes the statement a no-op once the legacy
--    FK has been dropped on a previous deploy.
ALTER TABLE lesson_progress
    DROP CONSTRAINT IF EXISTS lesson_progress_lesson_id_fkey;

-- 3) Drop the new composite FK if it already exists. Lets us re-add it
--    fresh on every deploy without tripping `duplicate_object`. Cost is a
--    brief ACCESS EXCLUSIVE lock on lesson_progress and a re-validation of
--    the FK against existing rows (cheap at our row counts).
ALTER TABLE lesson_progress
    DROP CONSTRAINT IF EXISTS lesson_progress_course_lesson_fkey;

-- 4) Add the composite FK with ON DELETE CASCADE so course/lesson deletes
--    still tear down progress.
ALTER TABLE lesson_progress
    ADD CONSTRAINT lesson_progress_course_lesson_fkey
    FOREIGN KEY (course_id, lesson_id)
    REFERENCES lessons (course_id, id)
    ON DELETE CASCADE;
