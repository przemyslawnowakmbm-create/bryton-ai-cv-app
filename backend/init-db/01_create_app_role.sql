-- Create the non-superuser application role for RLS enforcement.
-- PostgreSQL superusers always bypass RLS, so all tenant-scoped queries
-- must use this role to ensure Row-Level Security policies are enforced.
--
-- This script runs once on first container start via /docker-entrypoint-initdb.d/

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'bryton_app') THEN
        CREATE ROLE bryton_app WITH LOGIN PASSWORD 'bryton_dev';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE bryton TO bryton_app;
GRANT USAGE ON SCHEMA public TO bryton_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bryton_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bryton_app;

-- Ensure future tables created by the superuser also grant access to bryton_app
ALTER DEFAULT PRIVILEGES FOR ROLE bryton IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO bryton_app;
ALTER DEFAULT PRIVILEGES FOR ROLE bryton IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO bryton_app;
