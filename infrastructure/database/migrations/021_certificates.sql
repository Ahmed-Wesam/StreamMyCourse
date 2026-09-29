-- 021_certificates.sql
--
-- RS-12: course certificate codes + issued certificates table.
-- Idempotent where practical (IF NOT EXISTS). Pre-launch: backfill certificate
-- codes only (no certificate rows).

-- -------------------------- courses.certificate_code --------------------------
ALTER TABLE courses
    ADD COLUMN IF NOT EXISTS certificate_code CHAR(6);

-- Backfill existing rows with unique uppercase hex codes (retry on collision).
DO $$
DECLARE
    r RECORD;
    code TEXT;
    attempts INT;
BEGIN
    FOR r IN
        SELECT id FROM courses WHERE certificate_code IS NULL
    LOOP
        attempts := 0;
        LOOP
            attempts := attempts + 1;
            -- uuid-ossp (001_initial_schema): take 6 hex chars from a UUID.
            code := upper(substr(replace(uuid_generate_v4()::text, '-', ''), 1, 6));
            IF NOT EXISTS (
                SELECT 1 FROM courses c WHERE c.certificate_code = code
            ) THEN
                UPDATE courses SET certificate_code = code WHERE id = r.id;
                EXIT;
            END IF;
            IF attempts >= 20 THEN
                RAISE EXCEPTION
                    'Failed to generate unique certificate_code for course %',
                    r.id;
            END IF;
        END LOOP;
    END LOOP;
END $$;

ALTER TABLE courses
    ALTER COLUMN certificate_code SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS courses_certificate_code_key
    ON courses (certificate_code);

-- -------------------------- certificates --------------------------
CREATE TABLE IF NOT EXISTS certificates (
    id                UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_sub          VARCHAR(255) NOT NULL,
    course_id         UUID         NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    credential_id     VARCHAR(64)  NOT NULL,
    student_name      VARCHAR(255) NOT NULL,
    course_title      VARCHAR(255) NOT NULL,
    issue_date        DATE         NOT NULL,
    instructor_name   VARCHAR(255) NOT NULL,
    instructor_title  VARCHAR(255) NOT NULL,
    status            VARCHAR(20)  NOT NULL,
    revoked_at        TIMESTAMPTZ,
    revoked_by        VARCHAR(255),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT certificates_status_check CHECK (status IN ('valid', 'revoked')),
    CONSTRAINT certificates_credential_id_key UNIQUE (credential_id),
    CONSTRAINT certificates_user_course_key UNIQUE (user_sub, course_id)
);

CREATE INDEX IF NOT EXISTS idx_certificates_course
    ON certificates (course_id);

CREATE INDEX IF NOT EXISTS idx_certificates_user
    ON certificates (user_sub);
