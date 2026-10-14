-- 025_bundle_certificates.sql
--
-- Research Mastery Bundle certificate (one per user when all four pathway
-- course certificates are valid on distinct courses). Idempotent where practical.

CREATE TABLE IF NOT EXISTS bundle_certificates (
    id                UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_sub          VARCHAR(255) NOT NULL,
    credential_id     VARCHAR(64)  NOT NULL,
    student_name      VARCHAR(255) NOT NULL,
    issue_date        DATE         NOT NULL,
    instructor_name   VARCHAR(255) NOT NULL,
    instructor_title  VARCHAR(255) NOT NULL,
    status            VARCHAR(20)  NOT NULL,
    revoked_at        TIMESTAMPTZ,
    revoked_by        VARCHAR(255),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT bundle_certificates_status_check CHECK (status IN ('valid', 'revoked')),
    CONSTRAINT bundle_certificates_credential_id_key UNIQUE (credential_id),
    CONSTRAINT bundle_certificates_user_sub_key UNIQUE (user_sub)
);

CREATE INDEX IF NOT EXISTS idx_bundle_certificates_user
    ON bundle_certificates (user_sub);
