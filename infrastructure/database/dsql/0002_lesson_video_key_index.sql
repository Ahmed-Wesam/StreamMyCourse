CREATE INDEX ASYNC idx_lessons_video_key ON app.lessons (video_key) WHERE video_key <> '';

INSERT INTO app.schema_migrations (version) VALUES ('0002') ON CONFLICT (version) DO NOTHING;
