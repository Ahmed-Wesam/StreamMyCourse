CREATE UNIQUE INDEX ASYNC bundle_certificates_credential_id_upper ON app.bundle_certificates ((upper(credential_id)));

INSERT INTO app.schema_migrations (version) VALUES ('0004') ON CONFLICT (version) DO NOTHING;
