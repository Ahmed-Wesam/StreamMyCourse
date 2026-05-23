-- 013_student_active_session.sql
--
-- Student single-session: canonical active session id per user (empty = legacy / unset).
-- Idempotent: ADD COLUMN IF NOT EXISTS is safe to re-run on every deploy.

ALTER TABLE users ADD COLUMN IF NOT EXISTS student_active_session_id VARCHAR(64) NOT NULL DEFAULT '';
