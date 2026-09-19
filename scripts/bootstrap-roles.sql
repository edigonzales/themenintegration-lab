-- Synthetic local DML logins; the existing netl account remains the DDL user.
-- Works on existing Lab volumes without resetting databases or changing schemas.
DO $roles$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='netl_reader') THEN
    CREATE ROLE netl_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD 'netl-reader-local';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='netl_writer') THEN
    CREATE ROLE netl_writer LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD 'netl-writer-local';
  END IF;
END $roles$;
