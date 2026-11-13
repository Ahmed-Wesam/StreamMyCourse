DROP TABLE IF EXISTS app.enrollments;

INSERT INTO app.schema_migrations (version) VALUES ('0003') ON CONFLICT (version) DO NOTHING;
