-- 022_research_team.sql
--
-- RS-14: research team required courses + applications.
-- Idempotent where practical (IF NOT EXISTS).

-- -------------------------- research_team_required_courses --------------------------
CREATE TABLE IF NOT EXISTS research_team_required_courses (
    course_id UUID PRIMARY KEY REFERENCES courses(id) ON DELETE CASCADE
);

-- -------------------------- research_team_applications --------------------------
CREATE TABLE IF NOT EXISTS research_team_applications (
    id                     UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_sub               VARCHAR(255) NOT NULL,
    status                 VARCHAR(32)  NOT NULL,
    reapply_allowed        BOOLEAN      NOT NULL DEFAULT FALSE,
    submitted_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    full_name              VARCHAR(200) NOT NULL,
    email                  VARCHAR(320) NOT NULL,
    country                VARCHAR(100) NOT NULL,
    institution            VARCHAR(200) NOT NULL,
    position               VARCHAR(200) NOT NULL,
    publication_count      INT          NOT NULL,
    project_count          INT          NOT NULL,
    stats_experience       VARCHAR(32)  NOT NULL,
    sys_review_experience  VARCHAR(32)  NOT NULL,
    research_areas         TEXT[]       NOT NULL DEFAULT '{}',
    interests              TEXT         NOT NULL,
    motivation             TEXT         NOT NULL,
    weekly_hours           VARCHAR(64)  NOT NULL,
    acknowledged_at        TIMESTAMPTZ  NOT NULL,
    CONSTRAINT research_team_applications_status_check
        CHECK (status IN ('submitted', 'under_review', 'accepted', 'rejected')),
    CONSTRAINT research_team_applications_publication_count_check
        CHECK (publication_count >= 0 AND publication_count <= 9999),
    CONSTRAINT research_team_applications_project_count_check
        CHECK (project_count >= 0 AND project_count <= 9999)
);

CREATE UNIQUE INDEX IF NOT EXISTS research_team_applications_one_open
    ON research_team_applications (user_sub)
    WHERE status IN ('submitted', 'under_review');

CREATE UNIQUE INDEX IF NOT EXISTS research_team_applications_one_accepted
    ON research_team_applications (user_sub)
    WHERE status = 'accepted';

CREATE INDEX IF NOT EXISTS idx_research_team_applications_user
    ON research_team_applications (user_sub);

CREATE INDEX IF NOT EXISTS idx_research_team_applications_status
    ON research_team_applications (status);
