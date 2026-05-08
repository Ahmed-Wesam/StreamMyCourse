-- 004_enforce_course_created_by.sql
--
-- In-place upgrade that aligns existing RDS databases with the canonical
-- courses.created_by invariant in 001_initial_schema.sql:
-- - no implicit empty-string default
-- - non-null values must also be non-blank after trimming whitespace
--
-- Idempotency: DROP DEFAULT is a no-op in PostgreSQL when no default exists
-- (it does not error), so this file is safe to re-run on every deploy even
-- though it does not use IF EXISTS syntax for that statement.
--
-- Deployment safety: ADD CONSTRAINT is wrapped in a DO block. If any existing
-- course rows have blank created_by (possible from pre-enforcement inserts), the
-- constraint is skipped and a WARNING is emitted to the schema-apply Lambda log
-- instead of aborting the entire deployment. Operators must repair those rows
-- (UPDATE courses SET created_by = '<owner-sub>' WHERE btrim(created_by) = '')
-- and redeploy before the constraint takes effect on historical data. New inserts
-- are blocked immediately by the app-layer guard in service.py.

ALTER TABLE courses
    ALTER COLUMN created_by DROP DEFAULT;

DO $$
DECLARE
    bad_count INT;
BEGIN
    SELECT COUNT(*) INTO bad_count
    FROM courses
    WHERE btrim(created_by) = '';

    IF bad_count > 0 THEN
        RAISE WARNING
            '004_enforce_course_created_by: % course row(s) have blank '
            'created_by — ADD CONSTRAINT skipped. Repair with: '
            'UPDATE courses SET created_by = ''<owner-sub>'' '
            'WHERE btrim(created_by) = '''' '
            'then redeploy.',
            bad_count;
    ELSE
        EXECUTE 'ALTER TABLE courses DROP CONSTRAINT IF EXISTS courses_created_by_not_blank';
        EXECUTE 'ALTER TABLE courses ADD CONSTRAINT courses_created_by_not_blank CHECK (btrim(created_by) <> '''')';
    END IF;
END;
$$;
