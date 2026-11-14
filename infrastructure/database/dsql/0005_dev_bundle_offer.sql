INSERT INTO app.bundle_offers (environment, amount_minor, currency, active)
VALUES ('dev', 150000, 'JOD', TRUE)
ON CONFLICT (environment) DO NOTHING;

INSERT INTO app.schema_migrations (version) VALUES ('0005') ON CONFLICT (version) DO NOTHING;
