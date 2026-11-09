-- ============================================================================
-- MENTE SAUDAVEL - Script 03: STORED PROCEDURES
-- ----------------------------------------------------------------------------
-- REQUISITOS ATENDIDOS
--   [x] Stored procedure usada pela API (sp_criar_paciente, sp_agendar_consulta,
--       sp_registrar_evolucao).
--   [x] Stored procedure de relatorio que usa VIEW com JOIN + REFCURSOR
--       (sp_relatorio_atendimentos).
--   [x] Regras de negocio centralizadas no banco (duplicidade, idade minima,
--       conflito de agenda, evolucao unica).
-- POR QUE PROCEDURES: a regra fica no banco e vale para qualquer cliente
-- (painel web, Postman, app mobile), evitando duplicacao e inconsistencias.
-- Todas devolvem parametros OUT (id + mensagem) para a API distinguir sucesso
-- de erro de negocio sem depender de excecoes.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- PROCEDURE sp_criar_paciente
-- ----------------------------------------------------------------------------
-- PROPOSITO: cadastrar um paciente aplicando as regras de negocio antes do
-- INSERT: CPF unico, e-mail unico e idade minima de 5 anos.
-- USADA EM: POST /api/pacientes (app/routes/pacientes.py).
-- PARAMETROS DE ENTRADA:
--   p_nome, p_cpf, p_email, p_telefone, p_data_nascimento, p_genero,
--   p_cidade, p_observacoes.
-- PARAMETROS DE SAIDA:
--   p_id_paciente -> id gerado (NULL em caso de falha);
--   p_mensagem    -> texto amigavel exibido pela API.
-- POR QUE OUT EM VEZ DE EXCEPTION: permite devolver 409/422 com mensagem de
-- negocio sem abortar a transacao inteira; excecoes ficam para falhas reais.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_criar_paciente(
    p_nome            VARCHAR,   -- Nome completo do paciente
    p_cpf             VARCHAR,   -- CPF com 11 digitos (sem pontuacao)
    p_email           VARCHAR,   -- E-mail de contato
    p_telefone        VARCHAR,   -- Telefone com DDD (pode ser NULL)
    p_data_nascimento DATE,      -- Data de nascimento (nao futura)
    p_genero          VARCHAR,   -- Genero declarado
    p_cidade          VARCHAR,   -- Cidade de residencia (pode ser NULL)
    p_observacoes     TEXT,      -- Observacoes livres (pode ser NULL)
    OUT p_id_paciente INTEGER,   -- Id do paciente criado (NULL se falhar)
    OUT p_mensagem    TEXT       -- Mensagem de sucesso ou de erro de negocio
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_idade INTEGER;             -- Idade calculada em anos completos
BEGIN
    p_id_paciente := NULL;       -- Assume falha ate que o INSERT confirme

    -- Regra 1: CPF unico. Verificacao antecipada para devolver mensagem clara.
    IF EXISTS (SELECT 1 FROM pacientes WHERE cpf = p_cpf) THEN
        p_mensagem := 'Ja existe um paciente cadastrado com este CPF.';
        RETURN;
    END IF;

    -- Regra 2: e-mail unico, comparado sem diferenciar maiusculas/minusculas.
    IF EXISTS (SELECT 1 FROM pacientes WHERE lower(email) = lower(p_email)) THEN
        p_mensagem := 'Ja existe um paciente cadastrado com este e-mail.';
        RETURN;
    END IF;

    -- Regra 3: idade minima de 5 anos (idade completa, nao apenas ano).
    v_idade := date_part('year', age(p_data_nascimento));
    IF v_idade < 5 THEN
        p_mensagem := 'O paciente deve ter pelo menos 5 anos de idade.';
        RETURN;
    END IF;

    -- Insercao efetiva. As CHECKs/FKs do banco continuam valendo como ultima
    -- barreira de integridade, mesmo que esta procedure seja chamada direto.
    INSERT INTO pacientes (nome, cpf, email, telefone, data_nascimento,
                           genero, cidade, observacoes)
    VALUES (p_nome, p_cpf, p_email, p_telefone, p_data_nascimento,
            p_genero, p_cidade, p_observacoes)
    RETURNING id_paciente INTO p_id_paciente;

    p_mensagem := format('Paciente %s cadastrado com sucesso (id %s).',
                         p_nome, p_id_paciente);
EXCEPTION
    -- Corrida entre a verificacao e o INSERT: o UNIQUE do banco dispara aqui.
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
    IS 'Cadastra paciente validando CPF/e-mail unicos e idade minima; retorna id + mensagem';

-- ----------------------------------------------------------------------------
-- PROCEDURE sp_agendar_consulta
-- ----------------------------------------------------------------------------
-- PROPOSITO: agendar uma consulta validando:
--   1) paciente existe e esta ativo;
--   2) psicologo existe e esta ativo;
--   3) nao ha outro agendamento ativo no mesmo horario para o psicologo;
--   4) se nenhum valor for informado, usa o valor padrao do psicologo.
-- USADA EM: POST /api/consultas (app/routes/consultas.py).
-- PARAMETROS DE SAIDA:
--   p_id_consulta -> id gerado (NULL em caso de falha);
--   p_mensagem    -> mensagem de sucesso ou de erro de negocio.
-- POR QUE AQUI: a regra anti-conflito precisa ser atomica; centralizar no
-- banco evita que duas requisicoes simultaneas furem a agenda.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_agendar_consulta(
    p_id_paciente     INTEGER,    -- FK do paciente
    p_id_psicologo    INTEGER,    -- FK do psicologo
    p_data_hora       TIMESTAMPTZ,-- Data/hora de inicio
    p_duracao_minutos SMALLINT,   -- Duracao em minutos (15 a 180)
    p_modalidade      VARCHAR,    -- presencial ou online
    p_valor           NUMERIC,    -- Valor cobrado (NULL = valor do psicologo)
    p_observacoes     TEXT,       -- Observacoes do agendamento
    OUT p_id_consulta INTEGER,    -- Id da consulta criada (NULL se falhar)
    OUT p_mensagem    TEXT        -- Mensagem de sucesso ou erro de negocio
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_status_paciente VARCHAR;      -- Status atual do paciente
    v_ativo_psicologo BOOLEAN;      -- Se o psicologo aceita novos agendamentos
    v_valor_sessao    NUMERIC(10,2);-- Valor padrao do psicologo
BEGIN
    p_id_consulta := NULL;

    -- Validacao 1: paciente existe?
    SELECT status INTO v_status_paciente
      FROM pacientes
     WHERE id_paciente = p_id_paciente;

    IF NOT FOUND THEN
        p_mensagem := 'Paciente nao encontrado.';
        RETURN;
    END IF;

    -- Validacao 2: paciente ativo?
    IF v_status_paciente <> 'ativo' THEN
        p_mensagem := 'Paciente inativo nao pode agendar novas consultas.';
        RETURN;
    END IF;

    -- Validacao 3: psicologo existe? (aproveita para ler o valor padrao)
    SELECT ativo, valor_sessao INTO v_ativo_psicologo, v_valor_sessao
      FROM psicologos
     WHERE id_psicologo = p_id_psicologo;

    IF NOT FOUND THEN
        p_mensagem := 'Psicologo nao encontrado.';
        RETURN;
    END IF;

    -- Validacao 4: psicologo ativo?
    IF NOT v_ativo_psicologo THEN
        p_mensagem := 'Psicologo inativo nao recebe novos agendamentos.';
        RETURN;
    END IF;

    -- Validacao 5: conflito de horario (ignora consultas canceladas, pois o
    -- horario cancelado volta a ficar livre).
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

    -- Insercao: COALESCE garante o valor padrao quando p_valor vem NULL.
    INSERT INTO consultas (id_paciente, id_psicologo, data_hora, duracao_minutos,
                           modalidade, valor, observacoes)
    VALUES (p_id_paciente, p_id_psicologo, p_data_hora, p_duracao_minutos,
            p_modalidade, COALESCE(p_valor, v_valor_sessao), p_observacoes)
    RETURNING id_consulta INTO p_id_consulta;

    p_mensagem := format('Consulta agendada com sucesso (id %s).', p_id_consulta);
EXCEPTION
    -- O indice unico parcial tambem protege contra concorrencia.
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
    IS 'Agenda consulta validando paciente/psicologo ativos e conflito de horario';

-- ----------------------------------------------------------------------------
-- PROCEDURE sp_registrar_evolucao
-- ----------------------------------------------------------------------------
-- PROPOSITO: registrar a evolucao clinica de uma consulta, garantindo:
--   1) a consulta existe;
--   2) a consulta nao esta cancelada;
--   3) ainda nao existe evolucao para ela (1:1).
-- USADA EM: POST /api/evolucoes (app/routes/evolucoes.py).
-- PARAMETROS DE SAIDA:
--   p_id_evolucao -> id gerado (NULL em caso de falha);
--   p_mensagem    -> mensagem de sucesso ou de erro de negocio.
-- POR QUE AQUI: a unicidade da evolucao e uma regra clinica; manter no banco
-- evita prontuario duplicado mesmo com chamadas concorrentes.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_registrar_evolucao(
    p_id_consulta    INTEGER,   -- FK da consulta
    p_humor          SMALLINT,  -- Nota de humor de 1 a 10
    p_relato         TEXT,      -- Relato clinico (minimo 10 caracteres)
    p_encaminhamento VARCHAR,   -- Encaminhamento (pode ser NULL)
    OUT p_id_evolucao INTEGER,  -- Id da evolucao criada (NULL se falhar)
    OUT p_mensagem    TEXT      -- Mensagem de sucesso ou erro de negocio
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_status VARCHAR;           -- Status da consulta de origem
BEGIN
    p_id_evolucao := NULL;

    -- Validacao 1: a consulta existe?
    SELECT status INTO v_status
      FROM consultas
     WHERE id_consulta = p_id_consulta;

    IF NOT FOUND THEN
        p_mensagem := 'Consulta nao encontrada.';
        RETURN;
    END IF;

    -- Validacao 2: nao faz sentido evoluir consulta cancelada.
    IF v_status = 'cancelada' THEN
        p_mensagem := 'Nao e possivel registrar evolucao de consulta cancelada.';
        RETURN;
    END IF;

    -- Validacao 3: uma evolucao por consulta (regra 1:1).
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
    IS 'Registra a evolucao clinica de uma consulta (uma por consulta)';

-- ----------------------------------------------------------------------------
-- PROCEDURE sp_relatorio_atendimentos
-- ----------------------------------------------------------------------------
-- PROPOSITO: gerar o relatorio de atendimentos de um periodo usando a VIEW
-- vw_relatorio_atendimentos (que contem JOIN de consultas + pacientes +
-- psicologos + evolucoes) e devolver o resultado por REFCURSOR.
-- REQUISITO DO EDITAL: stored procedure que utiliza VIEW com JOIN.
-- NAO E CHAMADA PELA API: a API usa a funcao tabular
-- fn_relatorio_atendimentos, que le a mesma view.
-- PARAMETROS:
--   p_data_inicio -> primeiro dia do periodo (inclusive);
--   p_data_fim    -> ultimo dia do periodo (inclusive);
--   p_resultado   -> cursor aberto com as linhas do relatorio.
-- EXEMPLO DE USO:
--   BEGIN;
--   CALL sp_relatorio_atendimentos('2026-11-01', '2026-11-30', 'relatorio');
--   FETCH ALL FROM relatorio;
--   COMMIT;
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_relatorio_atendimentos(
    p_data_inicio DATE,          -- Inicio do periodo (inclusive)
    p_data_fim    DATE,          -- Fim do periodo (inclusive)
    INOUT p_resultado REFCURSOR  -- Cursor com as linhas do relatorio
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
