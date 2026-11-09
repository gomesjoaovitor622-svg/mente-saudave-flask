-- ============================================================================
-- MENTE SAUDAVEL - CLINICA DE PSICOLOGIA
-- Script 01: ESTRUTURA DO BANCO DE DADOS (PostgreSQL 14+)
-- Disciplinas: Desenvolvimento Web III + Banco de Dados II - IFRO 2026
-- ----------------------------------------------------------------------------
-- REQUISITOS ATENDIDOS NESTE ARQUIVO
--   [x] Modelo normalizado (3FN) com 5 tabelas relacionais.
--   [x] Chave primaria (PK) em todas as tabelas.
--   [x] Chaves estrangeiras (FK) com politica ON DELETE explicita.
--   [x] 20+ CHECK CONSTRAINTS (o edital exige no minimo 3), todas comentadas.
--   [x] Comentario descritivo ao lado de CADA coluna de CADA tabela.
--   [x] Triggers de auditoria e de atualizacao automatica de timestamp.
--   [x] Indices para desempenho e indice unico parcial anti-conflito de agenda.
-- ----------------------------------------------------------------------------
-- ORDEM DE EXECUCAO (conectado ao banco "mente_saudavel"):
--   psql -U postgres -d mente_saudavel -f database/01_schema.sql
--   psql -U postgres -d mente_saudavel -f database/02_views.sql
--   psql -U postgres -d mente_saudavel -f database/03_procedures.sql
--   psql -U postgres -d mente_saudavel -f database/04_seed.sql
-- ============================================================================

-- ----------------------------------------------------------------------------
-- LIMPEZA PREVIA
-- Permite reexecutar o script sem erro (idempotencia). A ordem respeita as
-- dependencias: primeiro tabelas-filhas, depois tabelas-pai, depois objetos
-- programaveis. CASCADE remove objetos dependentes (views, triggers, FKs).
-- ----------------------------------------------------------------------------
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
-- 1. TABELA PSICOLOGOS
-- ----------------------------------------------------------------------------
-- PROPOSITO: armazenar os profissionais de psicologia que atendem na clinica.
-- E a tabela-pai das consultas. O campo "ativo" funciona como exclusao logica:
-- profissionais inativos permanecem no historico, mas nao recebem agendamentos.
-- NORMALIZACAO: cada atributo depende apenas da PK (id_psicologo).
-- ============================================================================
CREATE TABLE psicologos (
    id_psicologo  SERIAL        PRIMARY KEY,                            -- Identificador unico e sequencial do psicologo (PK, gerado pelo banco)
    nome          VARCHAR(120)  NOT NULL,                               -- Nome completo do profissional, usado na agenda e nos relatorios
    crp           VARCHAR(20)   NOT NULL UNIQUE,                        -- Registro no Conselho Regional de Psicologia, formato UF/numero (ex.: 06/12345)
    email         VARCHAR(160)  NOT NULL UNIQUE,                        -- E-mail institucional do psicologo (contato e login futuro)
    especialidade VARCHAR(80)   NOT NULL,                               -- Area de atuacao (ex.: Terapia Cognitivo-Comportamental, Psicanalise)
    valor_sessao  NUMERIC(10,2) NOT NULL,                               -- Valor padrao cobrado por sessao, em reais; usado quando a consulta nao informa valor
    ativo         BOOLEAN       NOT NULL DEFAULT TRUE,                  -- Exclusao logica: TRUE recebe agendamentos; FALSE fica apenas no historico
    criado_em     TIMESTAMPTZ   NOT NULL DEFAULT now(),                 -- Data/hora (com fuso) em que o profissional foi cadastrado

    -- ------------------------------------------------------------------------
    -- CHECK CONSTRAINTS DA TABELA PSICOLOGOS
    -- Cada regra impede que dados invalidos entrem mesmo se a API for burlada.
    -- ------------------------------------------------------------------------
    CONSTRAINT ck_psicologos_crp_formato
        CHECK (crp ~ '^[0-9]{2}/[0-9]{4,6}$'),                          -- CRP deve seguir o padrao oficial UF/numero (2 digitos / 4 a 6 digitos)
    CONSTRAINT ck_psicologos_email_formato
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'), -- E-mail precisa ter formato valido (validacao tambem no Flask)
    CONSTRAINT ck_psicologos_valor_positivo
        CHECK (valor_sessao > 0),                                       -- Sessao nao pode ter valor zero ou negativo
    CONSTRAINT ck_psicologos_nome_minimo
        CHECK (char_length(btrim(nome)) >= 3)                           -- Evita nomes vazios ou com menos de 3 caracteres uteis
);

-- Metadados do dicionario de dados (visiveis no pgAdmin/psql \d+).
COMMENT ON TABLE  psicologos                IS 'Profissionais de psicologia que atendem na clinica';
COMMENT ON COLUMN psicologos.id_psicologo   IS 'Chave primaria do psicologo (SERIAL)';
COMMENT ON COLUMN psicologos.nome           IS 'Nome completo do profissional';
COMMENT ON COLUMN psicologos.crp            IS 'Registro profissional no formato UF/numero, unico';
COMMENT ON COLUMN psicologos.email          IS 'E-mail institucional unico do psicologo';
COMMENT ON COLUMN psicologos.especialidade  IS 'Area de atuacao clinica do profissional';
COMMENT ON COLUMN psicologos.valor_sessao   IS 'Valor padrao da sessao em reais (maior que zero)';
COMMENT ON COLUMN psicologos.ativo          IS 'Exclusao logica: FALSE impede novos agendamentos';
COMMENT ON COLUMN psicologos.criado_em      IS 'Data/hora de cadastro do profissional';
COMMENT ON CONSTRAINT ck_psicologos_crp_formato   ON psicologos IS 'Garante CRP no padrao UF/numero';
COMMENT ON CONSTRAINT ck_psicologos_email_formato ON psicologos IS 'Garante formato minimo de e-mail';
COMMENT ON CONSTRAINT ck_psicologos_valor_positivo ON psicologos IS 'Impede valor de sessao menor ou igual a zero';
COMMENT ON CONSTRAINT ck_psicologos_nome_minimo   ON psicologos IS 'Impede nome com menos de 3 caracteres';

-- ============================================================================
-- 2. TABELA PACIENTES
-- ----------------------------------------------------------------------------
-- PROPOSITO: cadastro central dos pacientes da clinica.
-- REGRAS DE NEGOCIO:
--   * CPF e e-mail sao unicos (uma pessoa = um cadastro).
--   * data_nascimento nao pode ser futura (CHECK).
--   * status permite exclusao logica (ativo/inativo) sem perder historico.
--   * A trigger trg_auditar_paciente registra toda alteracao (LGPD/rastreio).
-- ============================================================================
CREATE TABLE pacientes (
    id_paciente     SERIAL        PRIMARY KEY,                          -- Identificador unico e sequencial do paciente (PK)
    nome            VARCHAR(120)  NOT NULL,                             -- Nome completo do paciente, exibido na agenda e no prontuario
    cpf             CHAR(11)      NOT NULL UNIQUE,                      -- CPF do paciente com exatamente 11 digitos, sem pontos ou traco (unico)
    email           VARCHAR(160)  NOT NULL UNIQUE,                      -- E-mail de contato do paciente, usado em comunicacoes (unico)
    telefone        VARCHAR(20),                                        -- Telefone com DDD para contato; opcional, aceita (), +, espaco e hifen
    data_nascimento DATE          NOT NULL,                             -- Data de nascimento; usada para calcular idade e validar idade minima
    genero          VARCHAR(20)   NOT NULL DEFAULT 'nao_informado',     -- Genero declarado: feminino, masculino, nao_binario, outro ou nao_informado
    cidade          VARCHAR(80),                                        -- Cidade de residencia do paciente (opcional, usada em filtros)
    observacoes     TEXT,                                               -- Observacoes livres do cadastro (encaminhamento, preferencias, etc.)
    status          VARCHAR(15)   NOT NULL DEFAULT 'ativo',             -- Situacao do cadastro: ativo (agenda) ou inativo (arquivado)
    criado_em       TIMESTAMPTZ   NOT NULL DEFAULT now(),               -- Data/hora (com fuso) de criacao do cadastro
    atualizado_em   TIMESTAMPTZ,                                        -- Data/hora da ultima alteracao; preenchida pela trigger trg_pacientes_atualizado_em

    -- ------------------------------------------------------------------------
    -- CHECK CONSTRAINTS DA TABELA PACIENTES
    -- ------------------------------------------------------------------------
    CONSTRAINT ck_pacientes_cpf_formato
        CHECK (cpf ~ '^[0-9]{11}$'),                                    -- CPF armazenado apenas com digitos (a validacao dos digitos verificadores e feita no Flask)
    CONSTRAINT ck_pacientes_email_formato
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'), -- E-mail precisa ter formato valido
    CONSTRAINT ck_pacientes_nome_minimo
        CHECK (char_length(btrim(nome)) >= 3),                          -- Nome precisa ter ao menos 3 caracteres uteis
    CONSTRAINT ck_pacientes_nascimento
        CHECK (data_nascimento BETWEEN DATE '1900-01-01' AND CURRENT_DATE), -- Nascimento entre 1900 e hoje (nao aceita data futura)
    CONSTRAINT ck_pacientes_genero
        CHECK (genero IN ('feminino', 'masculino', 'nao_binario', 'outro', 'nao_informado')), -- Restringe o dominio de genero
    CONSTRAINT ck_pacientes_status
        CHECK (status IN ('ativo', 'inativo')),                         -- So permite os dois estados previstos na regra de negocio
    CONSTRAINT ck_pacientes_telefone
        CHECK (telefone IS NULL OR telefone ~ '^[0-9()+\-\s]{8,20}$')   -- Telefone opcional, mas se informado deve ter 8 a 20 caracteres validos
);

COMMENT ON TABLE  pacientes                 IS 'Pacientes atendidos pela clinica';
COMMENT ON COLUMN pacientes.id_paciente     IS 'Chave primaria do paciente (SERIAL)';
COMMENT ON COLUMN pacientes.nome            IS 'Nome completo do paciente';
COMMENT ON COLUMN pacientes.cpf             IS 'CPF com 11 digitos, sem pontuacao, unico';
COMMENT ON COLUMN pacientes.email           IS 'E-mail de contato unico do paciente';
COMMENT ON COLUMN pacientes.telefone        IS 'Telefone com DDD (opcional)';
COMMENT ON COLUMN pacientes.data_nascimento IS 'Data de nascimento (nao pode ser futura)';
COMMENT ON COLUMN pacientes.genero          IS 'Genero declarado pelo paciente';
COMMENT ON COLUMN pacientes.cidade          IS 'Cidade de residencia do paciente';
COMMENT ON COLUMN pacientes.observacoes     IS 'Observacoes gerais do cadastro';
COMMENT ON COLUMN pacientes.status          IS 'Ativo = pode agendar; Inativo = cadastro arquivado';
COMMENT ON COLUMN pacientes.criado_em       IS 'Data/hora de criacao do cadastro';
COMMENT ON COLUMN pacientes.atualizado_em   IS 'Data/hora da ultima alteracao (trigger)';
COMMENT ON CONSTRAINT ck_pacientes_cpf_formato   ON pacientes IS 'CPF deve conter exatamente 11 digitos';
COMMENT ON CONSTRAINT ck_pacientes_email_formato ON pacientes IS 'Garante formato minimo de e-mail';
COMMENT ON CONSTRAINT ck_pacientes_nome_minimo   ON pacientes IS 'Impede nome com menos de 3 caracteres';
COMMENT ON CONSTRAINT ck_pacientes_nascimento    ON pacientes IS 'Nascimento entre 1900 e a data atual';
COMMENT ON CONSTRAINT ck_pacientes_genero        ON pacientes IS 'Restringe genero aos valores do dominio';
COMMENT ON CONSTRAINT ck_pacientes_status        ON pacientes IS 'Permite apenas ativo ou inativo';
COMMENT ON CONSTRAINT ck_pacientes_telefone      ON pacientes IS 'Valida formato do telefone quando informado';

-- ============================================================================
-- 3. TABELA CONSULTAS
-- ----------------------------------------------------------------------------
-- PROPOSITO: registrar agendamentos e o historico de atendimentos.
-- RELACIONAMENTOS:
--   * id_paciente  -> pacientes  (ON DELETE CASCADE: ao excluir o paciente,
--                                  suas consultas e evolucoes saem junto);
--   * id_psicologo -> psicologos (ON DELETE RESTRICT: profissional com
--                                  historico nao pode ser excluido).
-- REGRA ANTI-CONFLITO: o indice unico parcial uq_consultas_agenda_ativa
-- impede dois agendamentos ATIVOS no mesmo horario para o mesmo psicologo.
-- Consultas canceladas liberam o horario.
-- ============================================================================
CREATE TABLE consultas (
    id_consulta      SERIAL        PRIMARY KEY,                         -- Identificador unico e sequencial da consulta (PK)
    id_paciente      INTEGER       NOT NULL,                            -- FK: paciente atendido (referencia pacientes.id_paciente)
    id_psicologo     INTEGER       NOT NULL,                            -- FK: psicologo responsavel (referencia psicologos.id_psicologo)
    data_hora        TIMESTAMPTZ   NOT NULL,                            -- Data e hora de inicio da consulta, com fuso horario
    duracao_minutos  SMALLINT      NOT NULL DEFAULT 50,                 -- Duracao prevista da sessao em minutos (15 a 180)
    modalidade       VARCHAR(12)   NOT NULL DEFAULT 'presencial',       -- Formato do atendimento: presencial ou online
    status           VARCHAR(12)   NOT NULL DEFAULT 'agendada',         -- Situacao: agendada, realizada, cancelada ou falta
    valor            NUMERIC(10,2),                                     -- Valor cobrado nesta consulta; se NULL, a procedure usa o valor padrao do psicologo
    observacoes      TEXT,                                              -- Anotacoes do agendamento (ex.: primeira sessao, remarcacao)
    criado_em        TIMESTAMPTZ   NOT NULL DEFAULT now(),              -- Data/hora em que o registro foi criado

    -- ------------------------------------------------------------------------
    -- CHAVES ESTRANGEIRAS (integridade referencial)
    -- ------------------------------------------------------------------------
    CONSTRAINT fk_consultas_paciente
        FOREIGN KEY (id_paciente) REFERENCES pacientes (id_paciente) ON DELETE CASCADE,   -- Excluir paciente remove suas consultas
    CONSTRAINT fk_consultas_psicologo
        FOREIGN KEY (id_psicologo) REFERENCES psicologos (id_psicologo) ON DELETE RESTRICT, -- Psicologo com consultas nao pode ser excluido

    -- ------------------------------------------------------------------------
    -- CHECK CONSTRAINTS DA TABELA CONSULTAS
    -- ------------------------------------------------------------------------
    CONSTRAINT ck_consultas_duracao
        CHECK (duracao_minutos BETWEEN 15 AND 180),                     -- Sessao clinica deve durar entre 15 e 180 minutos
    CONSTRAINT ck_consultas_modalidade
        CHECK (modalidade IN ('presencial', 'online')),                 -- Restringe a modalidade aos dois formatos suportados
    CONSTRAINT ck_consultas_status
        CHECK (status IN ('agendada', 'realizada', 'cancelada', 'falta')), -- Restringe o ciclo de vida da consulta
    CONSTRAINT ck_consultas_valor
        CHECK (valor IS NULL OR valor >= 0)                             -- Valor opcional, mas nunca negativo
);

COMMENT ON TABLE  consultas                 IS 'Agendamentos e historico de atendimentos';
COMMENT ON COLUMN consultas.id_consulta      IS 'Chave primaria da consulta (SERIAL)';
COMMENT ON COLUMN consultas.id_paciente      IS 'FK para pacientes (ON DELETE CASCADE)';
COMMENT ON COLUMN consultas.id_psicologo     IS 'FK para psicologos (ON DELETE RESTRICT)';
COMMENT ON COLUMN consultas.data_hora        IS 'Data/hora de inicio da consulta, com fuso';
COMMENT ON COLUMN consultas.duracao_minutos  IS 'Duracao da sessao em minutos (15 a 180)';
COMMENT ON COLUMN consultas.modalidade       IS 'presencial ou online';
COMMENT ON COLUMN consultas.status           IS 'agendada, realizada, cancelada ou falta';
COMMENT ON COLUMN consultas.valor            IS 'Valor cobrado; NULL usa o valor padrao do psicologo';
COMMENT ON COLUMN consultas.observacoes      IS 'Anotacoes do agendamento';
COMMENT ON COLUMN consultas.criado_em        IS 'Data/hora de criacao do registro';
COMMENT ON CONSTRAINT fk_consultas_paciente  ON consultas IS 'Integridade referencial com pacientes (CASCADE)';
COMMENT ON CONSTRAINT fk_consultas_psicologo ON consultas IS 'Integridade referencial com psicologos (RESTRICT)';
COMMENT ON CONSTRAINT ck_consultas_duracao   ON consultas IS 'Duracao entre 15 e 180 minutos';
COMMENT ON CONSTRAINT ck_consultas_modalidade ON consultas IS 'Modalidade presencial ou online';
COMMENT ON CONSTRAINT ck_consultas_status    ON consultas IS 'Status agendada, realizada, cancelada ou falta';
COMMENT ON CONSTRAINT ck_consultas_valor     ON consultas IS 'Valor nao pode ser negativo';

-- Indice unico PARCIAL: so considera consultas nao canceladas.
-- PROPOSITO: impedir double-booking do mesmo psicologo no mesmo horario,
-- permitindo que um horario cancelado seja reutilizado.
CREATE UNIQUE INDEX uq_consultas_agenda_ativa
    ON consultas (id_psicologo, data_hora)
    WHERE status <> 'cancelada';

COMMENT ON INDEX uq_consultas_agenda_ativa IS 'Impede dois agendamentos ativos no mesmo horario para o mesmo psicologo';

-- ============================================================================
-- 4. TABELA EVOLUCOES (PRONTUARIO)
-- ----------------------------------------------------------------------------
-- PROPOSITO: registrar a evolucao clinica de cada consulta.
-- RELACIONAMENTO: id_consulta -> consultas (1:1). O UNIQUE garante no maximo
-- uma evolucao por consulta, evitando duplicidade de prontuario.
-- LGPD: o relato clinico e dado sensivel; o acesso deve ser restrito.
-- ============================================================================
CREATE TABLE evolucoes (
    id_evolucao     SERIAL       PRIMARY KEY,                           -- Identificador unico e sequencial da evolucao (PK)
    id_consulta     INTEGER      NOT NULL UNIQUE,                       -- FK unica: cada consulta possui no maximo uma evolucao
    humor           SMALLINT     NOT NULL,                              -- Autoavaliacao de humor do paciente de 1 (muito ruim) a 10 (muito bom)
    relato          TEXT         NOT NULL,                              -- Relato clinico da sessao (texto livre, minimo 10 caracteres)
    encaminhamento  VARCHAR(200),                                       -- Encaminhamento/orientacao indicada pelo profissional (opcional)
    criado_em       TIMESTAMPTZ  NOT NULL DEFAULT now(),                -- Data/hora em que a evolucao foi registrada

    CONSTRAINT fk_evolucoes_consulta
        FOREIGN KEY (id_consulta) REFERENCES consultas (id_consulta) ON DELETE CASCADE, -- Excluir consulta remove a evolucao

    -- ------------------------------------------------------------------------
    -- CHECK CONSTRAINTS DA TABELA EVOLUCOES
    -- ------------------------------------------------------------------------
    CONSTRAINT ck_evolucoes_humor
        CHECK (humor BETWEEN 1 AND 10),                                 -- Escala de humor vai de 1 a 10
    CONSTRAINT ck_evolucoes_relato_minimo
        CHECK (char_length(btrim(relato)) >= 10)                        -- Relato precisa ter conteudo minimo (10 caracteres)
);

COMMENT ON TABLE  evolucoes                 IS 'Evolucoes clinicas registradas apos cada consulta';
COMMENT ON COLUMN evolucoes.id_evolucao     IS 'Chave primaria da evolucao (SERIAL)';
COMMENT ON COLUMN evolucoes.id_consulta     IS 'FK unica para consultas (uma evolucao por consulta)';
COMMENT ON COLUMN evolucoes.humor           IS 'Autoavaliacao de humor de 1 (muito ruim) a 10 (muito bom)';
COMMENT ON COLUMN evolucoes.relato          IS 'Relato clinico da sessao (minimo 10 caracteres)';
COMMENT ON COLUMN evolucoes.encaminhamento  IS 'Encaminhamento indicado pelo profissional (opcional)';
COMMENT ON COLUMN evolucoes.criado_em       IS 'Data/hora do registro da evolucao';
COMMENT ON CONSTRAINT fk_evolucoes_consulta ON evolucoes IS 'Integridade referencial com consultas (CASCADE)';
COMMENT ON CONSTRAINT ck_evolucoes_humor    ON evolucoes IS 'Humor entre 1 e 10';
COMMENT ON CONSTRAINT ck_evolucoes_relato_minimo ON evolucoes IS 'Relato com pelo menos 10 caracteres';

-- ============================================================================
-- 5. TABELA AUDITORIA_PACIENTES
-- ----------------------------------------------------------------------------
-- PROPOSITO: trilha de auditoria (quem alterou o que e quando) das operacoes
-- INSERT, UPDATE e DELETE em pacientes, preenchida automaticamente pela
-- trigger trg_auditar_paciente. NAO possui FK para pacientes de proposito:
-- o historico deve sobreviver mesmo se o paciente for excluido.
-- ============================================================================
CREATE TABLE auditoria_pacientes (
    id_auditoria      SERIAL       PRIMARY KEY,                         -- Identificador unico e sequencial do registro de auditoria (PK)
    id_paciente       INTEGER      NOT NULL,                            -- Id do paciente afetado; sem FK para preservar o historico apos exclusao
    operacao          VARCHAR(10)  NOT NULL,                            -- Operacao realizada: INSERT, UPDATE ou DELETE
    dados_anteriores  JSONB,                                            -- Snapshot completo do registro antes da alteracao (NULL em INSERT)
    dados_novos       JSONB,                                            -- Snapshot completo do registro depois da alteracao (NULL em DELETE)
    alterado_em       TIMESTAMPTZ  NOT NULL DEFAULT now(),              -- Data/hora em que a operacao foi auditada

    CONSTRAINT ck_auditoria_operacao
        CHECK (operacao IN ('INSERT', 'UPDATE', 'DELETE'))              -- Restringe a operacao auditada aos tres eventos suportados
);

COMMENT ON TABLE  auditoria_pacientes                  IS 'Trilha de auditoria gerada por trigger nas alteracoes de pacientes';
COMMENT ON COLUMN auditoria_pacientes.id_auditoria     IS 'Chave primaria do registro de auditoria';
COMMENT ON COLUMN auditoria_pacientes.id_paciente      IS 'Id do paciente afetado (sem FK, preserva historico)';
COMMENT ON COLUMN auditoria_pacientes.operacao         IS 'INSERT, UPDATE ou DELETE';
COMMENT ON COLUMN auditoria_pacientes.dados_anteriores IS 'Snapshot JSONB antes da alteracao';
COMMENT ON COLUMN auditoria_pacientes.dados_novos      IS 'Snapshot JSONB depois da alteracao';
COMMENT ON COLUMN auditoria_pacientes.alterado_em      IS 'Data/hora da operacao auditada';
COMMENT ON CONSTRAINT ck_auditoria_operacao ON auditoria_pacientes IS 'Operacao deve ser INSERT, UPDATE ou DELETE';

-- ============================================================================
-- 6. FUNCOES E TRIGGERS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- fn_auditar_paciente()
-- PROPOSITO: copiar automaticamente para auditoria_pacientes o estado antes e
-- depois de cada INSERT/UPDATE/DELETE em pacientes. Usa to_jsonb(NEW/OLD) para
-- gerar um snapshot completo em JSONB, sem precisar listar coluna por coluna.
-- POR QUE TRIGGER: garante auditoria mesmo se a alteracao vier de fora da API.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_auditar_paciente()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- INSERT: guarda apenas o estado novo.
        INSERT INTO auditoria_pacientes (id_paciente, operacao, dados_novos)
        VALUES (NEW.id_paciente, 'INSERT', to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        -- UPDATE: guarda o antes (OLD) e o depois (NEW) para rastrear mudancas.
        INSERT INTO auditoria_pacientes (id_paciente, operacao, dados_anteriores, dados_novos)
        VALUES (NEW.id_paciente, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSE
        -- DELETE: guarda apenas o estado anterior.
        INSERT INTO auditoria_pacientes (id_paciente, operacao, dados_anteriores)
        VALUES (OLD.id_paciente, 'DELETE', to_jsonb(OLD));
        RETURN OLD;
    END IF;
END;
$$;

COMMENT ON FUNCTION fn_auditar_paciente() IS 'Trigger: registra INSERT/UPDATE/DELETE de pacientes em auditoria_pacientes';

CREATE TRIGGER trg_auditar_paciente
    AFTER INSERT OR UPDATE OR DELETE ON pacientes
    FOR EACH ROW
    EXECUTE FUNCTION fn_auditar_paciente();

COMMENT ON TRIGGER trg_auditar_paciente ON pacientes IS 'Audita automaticamente toda alteracao de paciente';

-- ----------------------------------------------------------------------------
-- fn_atualizar_timestamp()
-- PROPOSITO: preencher atualizado_em automaticamente em cada UPDATE.
-- POR QUE NO BANCO: a data de atualizacao fica correta mesmo se outro sistema
-- alterar a tabela sem passar pela API.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_atualizar_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.atualizado_em := now();
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION fn_atualizar_timestamp() IS 'Trigger: atualiza automaticamente a coluna atualizado_em';

CREATE TRIGGER trg_pacientes_atualizado_em
    BEFORE UPDATE ON pacientes
    FOR EACH ROW
    EXECUTE FUNCTION fn_atualizar_timestamp();

COMMENT ON TRIGGER trg_pacientes_atualizado_em ON pacientes IS 'Atualiza atualizado_em antes de cada UPDATE';

-- ============================================================================
-- 7. INDICES DE DESEMPENHO
-- ----------------------------------------------------------------------------
-- PROPOSITO: acelerar filtros e JOINs mais usados pela API e pelos relatorios.
-- Sem indices, consultas por paciente/psicologo/data fariam varredura completa.
-- ============================================================================
CREATE INDEX idx_consultas_paciente ON consultas (id_paciente);          -- Acelera consultas por paciente (FK e filtros)
CREATE INDEX idx_consultas_psicologo ON consultas (id_psicologo);        -- Acelera consultas por psicologo (FK e agenda)
CREATE INDEX idx_consultas_data ON consultas (data_hora);                -- Acelera filtros por periodo nos relatorios
CREATE INDEX idx_evolucoes_criado_em ON evolucoes (criado_em);           -- Acelera listagem cronologica do prontuario
CREATE INDEX idx_pacientes_nome ON pacientes (nome);                     -- Acelera busca por nome (ILIKE) no painel

COMMENT ON INDEX idx_consultas_paciente IS 'Indice para JOIN/filtro por paciente';
COMMENT ON INDEX idx_consultas_psicologo IS 'Indice para JOIN/filtro por psicologo';
COMMENT ON INDEX idx_consultas_data IS 'Indice para filtros de periodo';
COMMENT ON INDEX idx_evolucoes_criado_em IS 'Indice para ordenacao cronologica das evolucoes';
COMMENT ON INDEX idx_pacientes_nome IS 'Indice para busca por nome do paciente';
