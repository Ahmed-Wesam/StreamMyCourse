-- 019_lesson_files_and_notes.sql
--
-- RS-11: instructor lesson attachments (resource/download) and private student notes.
-- Idempotent where practical (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS lesson_files (
    id             UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id      UUID         NOT NULL,
    lesson_id      UUID         NOT NULL,
    kind           VARCHAR(20)  NOT NULL,
    title          VARCHAR(255) NOT NULL,
    object_key     VARCHAR(500) NOT NULL DEFAULT '',
    content_type   VARCHAR(100) NOT NULL DEFAULT '',
    byte_size      BIGINT       NOT NULL DEFAULT 0,
    status         VARCHAR(20)  NOT NULL DEFAULT 'pending',
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT lesson_files_kind_check CHECK (kind IN ('resource', 'download')),
    CONSTRAINT lesson_files_status_check CHECK (status IN ('pending', 'ready')),
    CONSTRAINT lesson_files_byte_size_nonneg CHECK (byte_size >= 0),
    FOREIGN KEY (course_id, lesson_id) REFERENCES lessons (course_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lesson_files_lesson
    ON lesson_files (course_id, lesson_id);

CREATE TABLE IF NOT EXISTS lesson_notes (
    id             UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_sub       VARCHAR(255) NOT NULL REFERENCES users(user_sub) ON DELETE CASCADE,
    course_id      UUID         NOT NULL,
    lesson_id      UUID         NOT NULL,
    body           TEXT         NOT NULL,
    timestamp_sec  INTEGER,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT lesson_notes_timestamp_range CHECK (
        timestamp_sec IS NULL OR (timestamp_sec >= 0 AND timestamp_sec <= 86400)
    ),
    FOREIGN KEY (course_id, lesson_id) REFERENCES lessons (course_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lesson_notes_user_lesson
    ON lesson_notes (user_sub, lesson_id);
