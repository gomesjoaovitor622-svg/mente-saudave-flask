-- ============================================================================
-- Mente Saudavel - Script 00: criacao do banco de dados
-- Execute este arquivo conectado ao banco "postgres".
--   psql -U postgres -f database/00_create_database.sql
-- ============================================================================

SELECT 'CREATE DATABASE mente_saudavel WITH ENCODING ''UTF8'' TEMPLATE template0'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'mente_saudavel')\gexec

\echo 'Banco "mente_saudavel" pronto. Agora execute 01_schema.sql conectado a ele.'
