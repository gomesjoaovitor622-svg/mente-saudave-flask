-- ============================================================================
-- Mente Saudavel - Script 02: views e funcoes de consulta
-- Requisito: view com JOIN entre tabelas usada por stored procedure de
-- relatorio (vw_relatorio_atendimentos + sp_relatorio_atendimentos).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Agenda completa: consulta + paciente + psicologo
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_agenda_completa AS
SELECT c.id_consulta,
       c.data_hora,
       c.duracao_minutos,
       c.modalidade,
       c.status,
       c.valor,
       c.observacoes,
       p.id_paciente,
       p.nome  AS paciente,
       p.email AS paciente_email,
       ps.id_psicologo,
       ps.nome AS psicologo,
       ps.crp,
       ps.especialidade
  FROM consultas c
  JOIN pacientes  p  ON p.id_paciente  = c.id_paciente
  JOIN psicologos ps ON ps.id_psicologo = c.id_psicologo;

COMMENT ON VIEW vw_agenda_completa IS 'Agenda com dados de paciente e psicologo (JOIN de 3 tabelas)';

-- ----------------------------------------------------------------------------
-- Evolucoes com dados da consulta, paciente e psicologo
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_evolucoes AS
SELECT e.id_evolucao,
       e.id_consulta,
       c.id_paciente,
       p.nome  AS paciente,
       ps.nome AS psicologo,
       c.data_hora,
       e.humor,
       e.relato,
       e.encaminhamento,
       e.criado_em
  FROM evolucoes e
  JOIN consultas  c  ON c.id_consulta  = e.id_consulta
  JOIN pacientes  p  ON p.id_paciente  = c.id_paciente
  JOIN psicologos ps ON ps.id_psicologo = c.id_psicologo;

COMMENT ON VIEW vw_evolucoes IS 'Prontuario com dados do paciente e do profissional';

-- ----------------------------------------------------------------------------
-- Relatorio de atendimentos (VIEW com JOIN usada pela stored procedure)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_relatorio_atendimentos AS
SELECT c.id_consulta,
       c.data_hora,
       c.status,
       c.modalidade,
       c.valor,
       p.id_paciente,
       p.nome  AS paciente,
       ps.id_psicologo,
       ps.nome AS psicologo,
       ps.especialidade,
       e.humor,
       e.relato
  FROM consultas c
  JOIN pacientes  p  ON p.id_paciente  = c.id_paciente
  JOIN psicologos ps ON ps.id_psicologo = c.id_psicologo
  LEFT JOIN evolucoes e ON e.id_consulta = c.id_consulta;

COMMENT ON VIEW vw_relatorio_atendimentos IS 'Base do relatorio: consultas, pacientes, psicologos e evolucoes';

-- ----------------------------------------------------------------------------
-- Relatorio em formato de tabela (usado pela API)
-- A stored procedure sp_relatorio_atendimentos tambem usa esta view e atende
-- ao requisito da atividade (refcursor).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_relatorio_atendimentos(
    p_data_inicio DATE,
    p_data_fim DATE
)
RETURNS TABLE (
    id_consulta   INTEGER,
    data_hora     TIMESTAMPTZ,
    status        VARCHAR,
    modalidade    VARCHAR,
    valor         NUMERIC,
    id_paciente   INTEGER,
    paciente      VARCHAR,
    id_psicologo  INTEGER,
    psicologo     VARCHAR,
    especialidade VARCHAR,
    humor         SMALLINT,
    relato        TEXT
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
-- Resumo individual do paciente (cards da tela de detalhes)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_resumo_paciente(p_id_paciente INTEGER)
RETURNS TABLE (
    id_paciente          INTEGER,
    nome                 VARCHAR,
    total_consultas      BIGINT,
    consultas_realizadas BIGINT,
    consultas_agendadas  BIGINT,
    humor_medio          NUMERIC,
    ultima_consulta      TIMESTAMPTZ
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
