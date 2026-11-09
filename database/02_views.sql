-- ============================================================================
-- MENTE SAUDAVEL - Script 02: VIEWS E FUNCOES DE CONSULTA
-- ----------------------------------------------------------------------------
-- REQUISITOS ATENDIDOS
--   [x] VIEW com JOIN entre 3+ tabelas (vw_agenda_completa, vw_evolucoes,
--       vw_relatorio_atendimentos).
--   [x] View de relatorio usada pela stored procedure sp_relatorio_atendimentos.
--   [x] Funcoes tabulares consumidas pela API (fn_relatorio_atendimentos,
--       fn_resumo_paciente).
-- POR QUE USAR VIEWS: centralizam os JOINs e as regras de exibicao, evitando
-- repetir SQL na API e garantindo que painel, relatorios e procedures vejam
-- exatamente os mesmos dados.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- VIEW vw_agenda_completa
-- PROPOSITO: entregar a agenda "pronta para a tela", unindo consulta +
-- paciente + psicologo em uma unica linha. Evita que a API repita JOINs.
-- JOINs:
--   consultas c JOIN pacientes p  -> nome/e-mail do paciente;
--   consultas c JOIN psicologos ps -> nome/CRP/especialidade do profissional.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_agenda_completa AS
SELECT c.id_consulta,                    -- PK da consulta
       c.data_hora,                      -- Inicio da consulta (com fuso)
       c.duracao_minutos,                -- Duracao em minutos
       c.modalidade,                     -- presencial ou online
       c.status,                         -- agendada, realizada, cancelada ou falta
       c.valor,                          -- Valor cobrado
       c.observacoes,                    -- Anotacoes do agendamento
       p.id_paciente,                    -- PK do paciente (para edicao na tela)
       p.nome  AS paciente,              -- Nome do paciente (exibicao)
       p.email AS paciente_email,        -- E-mail do paciente
       ps.id_psicologo,                  -- PK do psicologo (para edicao na tela)
       ps.nome AS psicologo,             -- Nome do profissional (exibicao)
       ps.crp,                           -- Registro profissional
       ps.especialidade                  -- Area de atuacao
  FROM consultas c
  JOIN pacientes  p  ON p.id_paciente  = c.id_paciente
  JOIN psicologos ps ON ps.id_psicologo = c.id_psicologo;

COMMENT ON VIEW vw_agenda_completa IS 'Agenda com dados de paciente e psicologo (JOIN de 3 tabelas)';
COMMENT ON COLUMN vw_agenda_completa.paciente IS 'Nome do paciente obtido por JOIN';
COMMENT ON COLUMN vw_agenda_completa.psicologo IS 'Nome do psicologo obtido por JOIN';

-- ----------------------------------------------------------------------------
-- VIEW vw_evolucoes
-- PROPOSITO: montar o prontuario ja com paciente, psicologo e data da consulta.
-- Usada em GET /api/evolucoes e no historico clinico.
-- JOINs: evolucoes -> consultas -> pacientes -> psicologos.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_evolucoes AS
SELECT e.id_evolucao,          -- PK da evolucao
       e.id_consulta,          -- Consulta de origem
       c.id_paciente,          -- Paciente (para filtro por paciente)
       p.nome  AS paciente,    -- Nome do paciente
       ps.nome AS psicologo,   -- Nome do profissional
       c.data_hora,            -- Data/hora da consulta
       e.humor,                -- Nota de humor (1 a 10)
       e.relato,               -- Relato clinico
       e.encaminhamento,       -- Orientacao/encaminhamento
       e.criado_em             -- Data/hora do registro
  FROM evolucoes e
  JOIN consultas  c  ON c.id_consulta  = e.id_consulta
  JOIN pacientes  p  ON p.id_paciente  = c.id_paciente
  JOIN psicologos ps ON ps.id_psicologo = c.id_psicologo;

COMMENT ON VIEW vw_evolucoes IS 'Prontuario com dados do paciente e do profissional';
COMMENT ON COLUMN vw_evolucoes.paciente IS 'Nome do paciente obtido por JOIN';
COMMENT ON COLUMN vw_evolucoes.psicologo IS 'Nome do psicologo obtido por JOIN';

-- ----------------------------------------------------------------------------
-- VIEW vw_relatorio_atendimentos
-- PROPOSITO: base unica do relatorio de atendimentos. Combina consultas,
-- pacientes, psicologos e evolucoes.
-- POR QUE LEFT JOIN em evolucoes: consultas ainda sem evolucao (agendadas)
-- tambem devem aparecer no relatorio, com humor/relato nulos.
-- Esta view e consumida pela stored procedure sp_relatorio_atendimentos,
-- atendendo ao requisito "procedure que usa VIEW com JOIN".
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_relatorio_atendimentos AS
SELECT c.id_consulta,          -- PK da consulta
       c.data_hora,            -- Data/hora do atendimento
       c.status,               -- Situacao da consulta
       c.modalidade,           -- presencial ou online
       c.valor,                -- Valor cobrado
       p.id_paciente,          -- PK do paciente
       p.nome  AS paciente,    -- Nome do paciente
       ps.id_psicologo,        -- PK do psicologo
       ps.nome AS psicologo,   -- Nome do profissional
       ps.especialidade,       -- Especialidade do profissional
       e.humor,                -- Humor registrado na evolucao (pode ser NULL)
       e.relato                -- Relato registrado na evolucao (pode ser NULL)
  FROM consultas c
  JOIN pacientes  p  ON p.id_paciente  = c.id_paciente
  JOIN psicologos ps ON ps.id_psicologo = c.id_psicologo
  LEFT JOIN evolucoes e ON e.id_consulta = c.id_consulta;

COMMENT ON VIEW vw_relatorio_atendimentos IS 'Base do relatorio: consultas, pacientes, psicologos e evolucoes (LEFT JOIN)';

-- ----------------------------------------------------------------------------
-- FUNCAO fn_relatorio_atendimentos(data_inicio, data_fim)
-- PROPOSITO: devolver o relatorio em formato tabular (RETURNS TABLE) para a API.
-- POR QUE FUNCAO E NAO PROCEDURE: funcoes que retornam TABLE podem ser
-- consultadas com SELECT * FROM fn_relatorio_atendimentos(...), o que e mais
-- simples de consumir no Flask (psycopg2) do que um REFCURSOR.
-- A versao com REFCURSOR existe em sp_relatorio_atendimentos para atender
-- explicitamente ao requisito de stored procedure com view + JOIN.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_relatorio_atendimentos(
    p_data_inicio DATE,   -- Primeiro dia do periodo (inclusive)
    p_data_fim    DATE    -- Ultimo dia do periodo (inclusive)
)
RETURNS TABLE (
    id_consulta   INTEGER,   -- PK da consulta
    data_hora     TIMESTAMPTZ, -- Data/hora do atendimento
    status        VARCHAR,   -- Situacao da consulta
    modalidade    VARCHAR,   -- presencial ou online
    valor         NUMERIC,   -- Valor cobrado
    id_paciente   INTEGER,   -- PK do paciente
    paciente      VARCHAR,   -- Nome do paciente
    id_psicologo  INTEGER,   -- PK do psicologo
    psicologo     VARCHAR,   -- Nome do psicologo
    especialidade VARCHAR,   -- Especialidade
    humor         SMALLINT,  -- Humor da evolucao (NULL se nao houver)
    relato        TEXT       -- Relato da evolucao (NULL se nao houver)
)
LANGUAGE sql
STABLE
AS $$
    SELECT v.id_consulta,
           v.data_hora,
           v.status,
           v.modalidade,
           v.valor,
           v.id_paciente,
           v.paciente,
           v.id_psicologo,
           v.psicologo,
           v.especialidade,
           v.humor,
           v.relato
      FROM vw_relatorio_atendimentos v
     WHERE v.data_hora::date BETWEEN p_data_inicio AND p_data_fim
     ORDER BY v.data_hora;
$$;

COMMENT ON FUNCTION fn_relatorio_atendimentos(DATE, DATE) IS
    'Relatorio de atendimentos por periodo, lendo a view vw_relatorio_atendimentos';

-- ----------------------------------------------------------------------------
-- FUNCAO fn_resumo_paciente(id_paciente)
-- PROPOSITO: alimentar os cards da tela de detalhes do paciente.
-- Calcula, em uma unica consulta: total de consultas, realizadas, agendadas,
-- humor medio e data da ultima consulta.
-- POR QUE FILTER: permite calcular varios agregados condicionais sem
-- subconsultas repetidas, mantendo o codigo legivel e eficiente.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_resumo_paciente(p_id_paciente INTEGER)
RETURNS TABLE (
    id_paciente          INTEGER,    -- PK do paciente
    nome                 VARCHAR,    -- Nome do paciente
    total_consultas      BIGINT,     -- Todas as consultas do paciente
    consultas_realizadas BIGINT,     -- Consultas com status realizada
    consultas_agendadas  BIGINT,     -- Consultas com status agendada
    humor_medio          NUMERIC,    -- Media de humor das evolucoes
    ultima_consulta      TIMESTAMPTZ -- Data/hora da consulta mais recente
)
LANGUAGE sql
STABLE
AS $$
    SELECT p.id_paciente,
           p.nome,
           COUNT(c.id_consulta)                                        AS total_consultas,
           COUNT(c.id_consulta) FILTER (WHERE c.status = 'realizada')  AS consultas_realizadas,
           COUNT(c.id_consulta) FILTER (WHERE c.status = 'agendada')   AS consultas_agendadas,
           COALESCE(ROUND(AVG(e.humor), 1), 0)                         AS humor_medio,
           MAX(c.data_hora)                                            AS ultima_consulta
      FROM pacientes p
      LEFT JOIN consultas c ON c.id_paciente = p.id_paciente
      LEFT JOIN evolucoes e ON e.id_consulta = c.id_consulta
     WHERE p.id_paciente = p_id_paciente
     GROUP BY p.id_paciente, p.nome;
$$;

COMMENT ON FUNCTION fn_resumo_paciente(INTEGER) IS
    'Totais de consultas e humor medio de um paciente';
