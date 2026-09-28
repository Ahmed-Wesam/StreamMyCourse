-- 017_course_page_content.sql
--
-- RS-7: rich course marketing page JSON on courses.page_content.
-- Idempotent: ADD COLUMN IF NOT EXISTS is safe to re-run on every deploy.

ALTER TABLE courses ADD COLUMN IF NOT EXISTS page_content JSONB NOT NULL DEFAULT '{}'::jsonb;
