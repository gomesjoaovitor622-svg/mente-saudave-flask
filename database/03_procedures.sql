-- ============================================================================
-- Mente Saudavel - Script 03: stored procedures
-- ============================================================================

-- ----------------------------------------------------------------------------
-- sp_criar_paciente
-- Usada pela API no endpoint POST /api/pacientes.
-- Valida duplicidade, idade minima e devolve o id criado + mensagem.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_criar_paciente(
    p_nome            VARCHAR,
    p_cpf             VARCHAR,
    p_email           VARCHAR,
    p_telefone        VARCHAR,
    p_data_nascimento DATE,
    p_genero          VARCHAR,
    p_cidade          VARCHAR,
    p_observacoes     TEXT,
    OUT p_id_paciente INTEGER,
    OUT p_mensagem    TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_idade INTEGER;
BEGIN
    p_id_paciente := NULL;

    IF EXISTS (SELECT 1 FROM pacientes WHERE cpf = p_cpf) THEN
        p_mensagem := 'Ja existe um paciente cadastrado com este CPF.';
        RETURN;
    END IF;

    IF EXISTS (SELECT 1 FROM pacientes WHERE lower(email) = lower(p_email)) THEN
        p_mensagem := 'Ja existe um paciente cadastrado com este e-mail.';
        RETURN;
    END IF;

    v_idade := date_part('year', age(p_data_nascimento));
    IF v_idade < 5 THEN
        p_mensagem := 'O paciente deve ter pelo menos 5 anos de idade.';
        RETURN;
    END IF;

    INSERT INTO pacientes (nome, cpf, email, telefone, data_nascimento,
                           genero, cidade, observacoes)
    VALUES (p_nome, p_cpf, p_email, p_telefone, p_data_nascimento,
            p_genero, p_cidade, p_observacoes)
    RETURNING id_paciente INTO p_id_paciente;

    p_mensagem := format('Paciente %s cadastrado com sucesso (id %s).',
                         p_nome, p_id_paciente);
EXCEPTION
    WHEN unique_violation THEN
        p_id_paciente := NULL;
        p_mensagem := 'CPF ou e-mail ja cadastrado para outro paciente.';
    WHEN check_violation THEN
        p_id_paciente := NULL;
        p_mensagem := 'Dados do paciente violam uma regra de validacao do banco.';
    WHEN OTHERS THEN
        p_id_paciente := NULL;
        p_mensagem := 'Erro ao cadastrar paciente: ' || SQLERRM;
END;
$$;

COMMENT ON PROCEDURE sp_criar_paciente(VARCHAR, VARCHAR, VARCHAR, VARCHAR, DATE, VARCHAR, VARCHAR, TEXT)
    IS 'Cadastra paciente com validacoes e retorna id + mensagem';

-- ----------------------------------------------------------------------------
-- sp_agendar_consulta
-- Usada pela API no endpoint POST /api/consultas.
-- Verifica paciente/psicologo, conflito de horario e usa o valor padrao do
-- psicologo quando nenhum valor e informado.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_agendar_consulta(
    p_id_paciente     INTEGER,
    p_id_psicologo    INTEGER,
    p_data_hora       TIMESTAMPTZ,
    p_duracao_minutos SMALLINT,
    p_modalidade      VARCHAR,
    p_valor           NUMERIC,
    p_observacoes     TEXT,
    OUT p_id_consulta INTEGER,
    OUT p_mensagem    TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_status_paciente VARCHAR;
    v_ativo_psicologo BOOLEAN;
    v_valor_sessao    NUMERIC(10,2);
BEGIN
    p_id_consulta := NULL;

    SELECT status INTO v_status_paciente
      FROM pacientes
     WHERE id_paciente = p_id_paciente;

    IF NOT FOUND THEN
        p_mensagem := 'Paciente nao encontrado.';
        RETURN;
    END IF;

    IF v_status_paciente <> 'ativo' THEN
        p_mensagem := 'Paciente inativo nao pode agendar novas consultas.';
        RETURN;
    END IF;

    SELECT ativo, valor_sessao INTO v_ativo_psicologo, v_valor_sessao
      FROM psicologos
     WHERE id_psicologo = p_id_psicologo;

    IF NOT FOUND THEN
        p_mensagem := 'Psicologo nao encontrado.';
        RETURN;
    END IF;

    IF NOT v_ativo_psicologo THEN
        p_mensagem := 'Psicologo inativo nao recebe novos agendamentos.';
        RETURN;
    END IF;

    IF EXISTS (
        SELECT 1
          FROM consultas
         WHERE id_psicologo = p_id_psicologo
           AND data_hora = p_data_hora
           AND status <> 'cancelada'
    ) THEN
        p_mensagem := 'Horario ja ocupado para este psicologo.';
        RETURN;
    END IF;

    INSERT INTO consultas (id_paciente, id_psicologo, data_hora, duracao_minutos,
                           modalidade, valor, observacoes)
    VALUES (p_id_paciente, p_id_psicologo, p_data_hora, p_duracao_minutos,
            p_modalidade, COALESCE(p_valor, v_valor_sessao), p_observacoes)
    RETURNING id_consulta INTO p_id_consulta;

    p_mensagem := format('Consulta agendada com sucesso (id %s).', p_id_consulta);
EXCEPTION
    WHEN unique_violation THEN
        p_id_consulta := NULL;
        p_mensagem := 'Horario ja ocupado para este psicologo.';
    WHEN check_violation THEN
        p_id_consulta := NULL;
        p_mensagem := 'Dados da consulta violam uma regra de validacao do banco.';
    WHEN OTHERS THEN
        p_id_consulta := NULL;
        p_mensagem := 'Erro ao agendar consulta: ' || SQLERRM;
END;
$$;

COMMENT ON PROCEDURE sp_agendar_consulta(INTEGER, INTEGER, TIMESTAMPTZ, SMALLINT, VARCHAR, NUMERIC, TEXT)
    IS 'Agenda consulta validando paciente, psicologo e conflito de horario';

-- ----------------------------------------------------------------------------
-- sp_registrar_evolucao
-- Usada pela API no endpoint POST /api/evolucoes.
-- Garante uma unica evolucao por consulta.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_registrar_evolucao(
    p_id_consulta    INTEGER,
    p_humor          SMALLINT,
    p_relato         TEXT,
    p_encaminhamento VARCHAR,
    OUT p_id_evolucao INTEGER,
    OUT p_mensagem    TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_status VARCHAR;
BEGIN
    p_id_evolucao := NULL;

    SELECT status INTO v_status
      FROM consultas
     WHERE id_consulta = p_id_consulta;

    IF NOT FOUND THEN
        p_mensagem := 'Consulta nao encontrada.';
        RETURN;
    END IF;

    IF v_status = 'cancelada' THEN
        p_mensagem := 'Nao e possivel registrar evolucao de consulta cancelada.';
        RETURN;
    END IF;

    IF EXISTS (SELECT 1 FROM evolucoes WHERE id_consulta = p_id_consulta) THEN
        p_mensagem := 'Esta consulta ja possui uma evolucao registrada.';
        RETURN;
    END IF;

    INSERT INTO evolucoes (id_consulta, humor, relato, encaminhamento)
    VALUES (p_id_consulta, p_humor, p_relato, p_encaminhamento)
    RETURNING id_evolucao INTO p_id_evolucao;

    p_mensagem := format('Evolucao registrada com sucesso (id %s).', p_id_evolucao);
EXCEPTION
    WHEN check_violation THEN
        p_id_evolucao := NULL;
        p_mensagem := 'Dados da evolucao violam uma regra de validacao do banco.';
    WHEN OTHERS THEN
        p_id_evolucao := NULL;
        p_mensagem := 'Erro ao registrar evolucao: ' || SQLERRM;
END;
$$;

COMMENT ON PROCEDURE sp_registrar_evolucao(INTEGER, SMALLINT, TEXT, VARCHAR)
    IS 'Registra a evolucao clinica de uma consulta';

-- ----------------------------------------------------------------------------
-- sp_relatorio_atendimentos
-- REQUISITO da atividade: stored procedure que utiliza uma VIEW com JOIN
-- entre tabelas para gerar um relatorio. Nao e chamada pela API.
--
-- Exemplo de uso:
--   BEGIN;
--   CALL sp_relatorio_atendimentos('2026-11-01', '2026-11-30', 'relatorio');
--   FETCH ALL FROM relatorio;
--   COMMIT;
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_relatorio_atendimentos(
    p_data_inicio DATE,
    p_data_fim    DATE,
    INOUT p_resultado REFCURSOR
)
LANGUAGE plpgsql
AS $$
BEGIN
    OPEN p_resultado FOR
        SELECT v.id_consulta,
               v.data_hora,
               v.paciente,
               v.psicologo,
               v.especialidade,
               v.status,
               v.modalidade,
               v.valor,
               v.humor
          FROM vw_relatorio_atendimentos v
         WHERE v.data_hora::date BETWEEN p_data_inicio AND p_data_fim
         ORDER BY v.data_hora;
END;
$$;

COMMENT ON PROCEDURE sp_relatorio_atendimentos(DATE, DATE, REFCURSOR)
    IS 'Relatorio por periodo usando a view vw_relatorio_atendimentos (refcursor)';
