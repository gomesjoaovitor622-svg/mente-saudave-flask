-- ============================================================================
-- Mente Saudavel - Clinica de Psicologia
-- Script 01: estrutura do banco de dados (PostgreSQL 14+)
-- Disciplinas: Desenvolvimento Web III + Banco de Dados II
--
-- Ordem de execucao:
--   psql -U postgres -f database/01_schema.sql
--   psql -U postgres -d mente_saudavel -f database/02_views.sql
--   psql -U postgres -d mente_saudavel -f database/03_procedures.sql
--   psql -U postgres -d mente_saudavel -f database/04_seed.sql
-- ============================================================================

-- Remove objetos para permitir reexecucao do script -------------------------
DROP TABLE IF EXISTS auditoria_pacientes CASCADE;
DROP TABLE IF EXISTS evolucoes CASCADE;
DROP TABLE IF EXISTS consultas CASCADE;
DROP TABLE IF EXISTS pacientes CASCADE;
DROP TABLE IF EXISTS psicologos CASCADE;
DROP VIEW IF EXISTS vw_agenda_completa CASCADE;
DROP VIEW IF EXISTS vw_evolucoes CASCADE;
DROP VIEW IF EXISTS vw_relatorio_atendimentos CASCADE;
DROP FUNCTION IF EXISTS fn_resumo_paciente(INTEGER) CASCADE;
DROP FUNCTION IF EXISTS fn_relatorio_atendimentos(DATE, DATE) CASCADE;
DROP PROCEDURE IF EXISTS sp_criar_paciente CASCADE;
DROP PROCEDURE IF EXISTS sp_agendar_consulta CASCADE;
DROP PROCEDURE IF EXISTS sp_registrar_evolucao CASCADE;
DROP PROCEDURE IF EXISTS sp_relatorio_atendimentos CASCADE;

-- ============================================================================
-- 1. PSICOLOGOS
-- ============================================================================
CREATE TABLE psicologos (
    id_psicologo  SERIAL        PRIMARY KEY,
    nome          VARCHAR(120)  NOT NULL,                            -- Nome completo do profissional
    crp           VARCHAR(20)   NOT NULL UNIQUE,                     -- Registro no Conselho Regional de Psicologia (ex.: 06/12345)
    email         VARCHAR(160)  NOT NULL UNIQUE,                     -- E-mail institucional do psicologo
    especialidade VARCHAR(80)   NOT NULL,                            -- Area de atuacao (ex.: Terapia Cognitivo-Comportamental)
    valor_sessao  NUMERIC(10,2) NOT NULL,                            -- Valor padrao da sessao em reais
    ativo         BOOLEAN       NOT NULL DEFAULT TRUE,               -- Indica se o profissional recebe novos agendamentos
    criado_em     TIMESTAMPTZ   NOT NULL DEFAULT now(),              -- Data/hora de cadastro

    -- check constraints (validacao no banco)
    CONSTRAINT ck_psicologos_crp_formato
        CHECK (crp ~ '^[0-9]{2}/[0-9]{4,6}$'),
    CONSTRAINT ck_psicologos_email_formato
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT ck_psicologos_valor_positivo
        CHECK (valor_sessao > 0),
    CONSTRAINT ck_psicologos_nome_minimo
        CHECK (char_length(btrim(nome)) >= 3)
);

COMMENT ON TABLE psicologos IS 'Profissionais de psicologia que atendem na clinica';
COMMENT ON COLUMN psicologos.id_psicologo IS 'Chave primaria do psicologo';
COMMENT ON COLUMN psicologos.crp IS 'Registro profissional no formato UF/numero';
COMMENT ON COLUMN psicologos.valor_sessao IS 'Valor padrao cobrado por sessao';

-- ============================================================================
-- 2. PACIENTES
-- ============================================================================
CREATE TABLE pacientes (
    id_paciente     SERIAL        PRIMARY KEY,
    nome            VARCHAR(120)  NOT NULL,                          -- Nome completo do paciente
    cpf             CHAR(11)      NOT NULL UNIQUE,                   -- CPF sem pontuacao (11 digitos)
    email           VARCHAR(160)  NOT NULL UNIQUE,                   -- E-mail de contato do paciente
    telefone        VARCHAR(20),                                     -- Telefone com DDD (opcional)
    data_nascimento DATE          NOT NULL,                          -- Data de nascimento do paciente
    genero          VARCHAR(20)   NOT NULL DEFAULT 'nao_informado',  -- Genero declarado pelo paciente
    cidade          VARCHAR(80),                                     -- Cidade onde o paciente reside
    observacoes     TEXT,                                            -- Observacoes gerais do cadastro
    status          VARCHAR(15)   NOT NULL DEFAULT 'ativo',          -- Situacao do cadastro: ativo ou inativo
    criado_em       TIMESTAMPTZ   NOT NULL DEFAULT now(),            -- Data/hora de cadastro
    atualizado_em   TIMESTAMPTZ,                                     -- Data/hora da ultima alteracao

    -- check constraints (validacao no banco)
    CONSTRAINT ck_pacientes_cpf_formato
        CHECK (cpf ~ '^[0-9]{11}$'),
    CONSTRAINT ck_pacientes_email_formato
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT ck_pacientes_nome_minimo
        CHECK (char_length(btrim(nome)) >= 3),
    CONSTRAINT ck_pacientes_nascimento
        CHECK (data_nascimento BETWEEN DATE '1900-01-01' AND CURRENT_DATE),
    CONSTRAINT ck_pacientes_genero
        CHECK (genero IN ('feminino', 'masculino', 'nao_binario', 'outro', 'nao_informado')),
    CONSTRAINT ck_pacientes_status
        CHECK (status IN ('ativo', 'inativo')),
    CONSTRAINT ck_pacientes_telefone
        CHECK (telefone IS NULL OR telefone ~ '^[0-9()+\-\s]{8,20}$')
);

COMMENT ON TABLE pacientes IS 'Pacientes atendidos pela clinica';
COMMENT ON COLUMN pacientes.id_paciente IS 'Chave primaria do paciente';
COMMENT ON COLUMN pacientes.cpf IS 'CPF do paciente, somente digitos';
COMMENT ON COLUMN pacientes.data_nascimento IS 'Data de nascimento (nao pode ser futura)';
COMMENT ON COLUMN pacientes.status IS 'Ativo = pode agendar; Inativo = cadastro arquivado';

-- ============================================================================
-- 3. CONSULTAS
-- ============================================================================
CREATE TABLE consultas (
    id_consulta      SERIAL        PRIMARY KEY,
    id_paciente      INTEGER       NOT NULL,                         -- FK: paciente atendido
    id_psicologo     INTEGER       NOT NULL,                         -- FK: psicologo responsavel
    data_hora        TIMESTAMPTZ   NOT NULL,                         -- Data e hora de inicio da consulta
    duracao_minutos  SMALLINT      NOT NULL DEFAULT 50,              -- Duracao da sessao em minutos
    modalidade       VARCHAR(12)   NOT NULL DEFAULT 'presencial',    -- Formato: presencial ou online
    status           VARCHAR(12)   NOT NULL DEFAULT 'agendada',      -- Situacao da consulta
    valor            NUMERIC(10,2),                                  -- Valor cobrado (se nulo, usa o valor do psicologo)
    observacoes      TEXT,                                           -- Anotacoes do agendamento
    criado_em        TIMESTAMPTZ   NOT NULL DEFAULT now(),           -- Data/hora do registro

    CONSTRAINT fk_consultas_paciente
        FOREIGN KEY (id_paciente) REFERENCES pacientes (id_paciente) ON DELETE CASCADE,
    CONSTRAINT fk_consultas_psicologo
        FOREIGN KEY (id_psicologo) REFERENCES psicologos (id_psicologo) ON DELETE RESTRICT,

    -- check constraints (validacao no banco)
    CONSTRAINT ck_consultas_duracao
        CHECK (duracao_minutos BETWEEN 15 AND 180),
    CONSTRAINT ck_consultas_modalidade
        CHECK (modalidade IN ('presencial', 'online')),
    CONSTRAINT ck_consultas_status
        CHECK (status IN ('agendada', 'realizada', 'cancelada', 'falta')),
    CONSTRAINT ck_consultas_valor
        CHECK (valor IS NULL OR valor >= 0)
);

COMMENT ON TABLE consultas IS 'Agendamentos e historico de atendimentos';
COMMENT ON COLUMN consultas.id_paciente IS 'FK para pacientes';
COMMENT ON COLUMN consultas.id_psicologo IS 'FK para psicologos';
COMMENT ON COLUMN consultas.status IS 'agendada, realizada, cancelada ou falta';

-- Impede dois agendamentos no mesmo horario para o mesmo psicologo.
-- Consultas canceladas liberam o horario.
CREATE UNIQUE INDEX uq_consultas_agenda_ativa
    ON consultas (id_psicologo, data_hora)
    WHERE status <> 'cancelada';

-- ============================================================================
-- 4. EVOLUCOES (prontuario)
-- ============================================================================
CREATE TABLE evolucoes (
    id_evolucao     SERIAL       PRIMARY KEY,
    id_consulta     INTEGER      NOT NULL UNIQUE,                    -- FK: consulta registrada (1 evolucao por consulta)
    humor           SMALLINT     NOT NULL,                           -- Nota de humor do paciente (1 a 10)
    relato          TEXT         NOT NULL,                           -- Relato clinico da sessao
    encaminhamento  VARCHAR(200),                                    -- Encaminhamento indicado pelo profissional
    criado_em       TIMESTAMPTZ  NOT NULL DEFAULT now(),             -- Data/hora do registro

    CONSTRAINT fk_evolucoes_consulta
        FOREIGN KEY (id_consulta) REFERENCES consultas (id_consulta) ON DELETE CASCADE,

    -- check constraints (validacao no banco)
    CONSTRAINT ck_evolucoes_humor
        CHECK (humor BETWEEN 1 AND 10),
    CONSTRAINT ck_evolucoes_relato_minimo
        CHECK (char_length(btrim(relato)) >= 10)
);

COMMENT ON TABLE evolucoes IS 'Evolucoes clinicas registradas apos cada consulta';
COMMENT ON COLUMN evolucoes.id_consulta IS 'FK unica para consultas (uma evolucao por consulta)';
COMMENT ON COLUMN evolucoes.humor IS 'Autoavaliacao de humor de 1 (muito ruim) a 10 (muito bom)';

-- ============================================================================
-- 5. AUDITORIA DE PACIENTES (trigger)
-- ============================================================================
CREATE TABLE auditoria_pacientes (
    id_auditoria      SERIAL       PRIMARY KEY,
    id_paciente       INTEGER      NOT NULL,                          -- Id do paciente afetado (sem FK: preserva historico)
    operacao          VARCHAR(10)  NOT NULL,                          -- INSERT, UPDATE ou DELETE
    dados_anteriores  JSONB,                                          -- Snapshot antes da alteracao
    dados_novos       JSONB,                                          -- Snapshot depois da alteracao
    alterado_em       TIMESTAMPTZ  NOT NULL DEFAULT now(),            -- Data/hora da operacao

    CONSTRAINT ck_auditoria_operacao
        CHECK (operacao IN ('INSERT', 'UPDATE', 'DELETE'))
);

COMMENT ON TABLE auditoria_pacientes IS 'Trilha de auditoria gerada por trigger nas alteracoes de pacientes';

-- Funcao do trigger de auditoria --------------------------------------------
CREATE OR REPLACE FUNCTION fn_auditar_paciente()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO auditoria_pacientes (id_paciente, operacao, dados_novos)
        VALUES (NEW.id_paciente, 'INSERT', to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO auditoria_pacientes (id_paciente, operacao, dados_anteriores, dados_novos)
        VALUES (NEW.id_paciente, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSE
        INSERT INTO auditoria_pacientes (id_paciente, operacao, dados_anteriores)
        VALUES (OLD.id_paciente, 'DELETE', to_jsonb(OLD));
        RETURN OLD;
    END IF;
END;
$$;

CREATE TRIGGER trg_auditar_paciente
    AFTER INSERT OR UPDATE OR DELETE ON pacientes
    FOR EACH ROW
    EXECUTE FUNCTION fn_auditar_paciente();

-- Funcao do trigger de atualizado_em ----------------------------------------
CREATE OR REPLACE FUNCTION fn_atualizar_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.atualizado_em := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_pacientes_atualizado_em
    BEFORE UPDATE ON pacientes
    FOR EACH ROW
    EXECUTE FUNCTION fn_atualizar_timestamp();

-- Indices auxiliares para consultas frequentes ------------------------------
CREATE INDEX idx_consultas_paciente ON consultas (id_paciente);
CREATE INDEX idx_consultas_psicologo ON consultas (id_psicologo);
CREATE INDEX idx_consultas_data ON consultas (data_hora);
CREATE INDEX idx_evolucoes_criado_em ON evolucoes (criado_em);
CREATE INDEX idx_pacientes_nome ON pacientes (nome);
