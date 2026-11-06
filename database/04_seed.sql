-- ============================================================================
-- Mente Saudavel - Script 04: dados de exemplo (seed)
-- Datas relativas a hoje para que a agenda e os relatorios sempre tenham
-- registros recentes.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Psicologos
-- ----------------------------------------------------------------------------
INSERT INTO psicologos (id_psicologo, nome, crp, email, especialidade, valor_sessao, ativo)
VALUES
    (1, 'Ana Paula Ribeiro',  '06/12345', 'ana.ribeiro@mentesaudavel.com',  'Terapia Cognitivo-Comportamental', 180.00, TRUE),
    (2, 'Carlos Eduardo Lima', '06/54321', 'carlos.lima@mentesaudavel.com',  'Psicanalise',                      200.00, TRUE),
    (3, 'Mariana Souza Alves', '06/98765', 'mariana.alves@mentesaudavel.com', 'Neuropsicologia',                  220.00, TRUE);

-- ----------------------------------------------------------------------------
-- Pacientes (CPFs validos, apenas digitos)
-- ----------------------------------------------------------------------------
INSERT INTO pacientes (id_paciente, nome, cpf, email, telefone, data_nascimento,
                       genero, cidade, observacoes, status)
VALUES
    (1, 'Joao Pedro Martins',    '52998224725', 'joao.martins@email.com',
        '(69) 99999-1001', DATE '1995-04-12', 'masculino', 'Porto Velho',
        'Encaminhado pela clinica-escola.', 'ativo'),
    (2, 'Maria Clara Santos',    '11144477735', 'maria.santos@email.com',
        '(69) 99999-1002', DATE '1990-08-23', 'feminino', 'Porto Velho',
        'Prefere atendimento no periodo da manha.', 'ativo'),
    (3, 'Lucas Ferreira Gomes',  '12345678909', 'lucas.gomes@email.com',
        '(69) 99999-1003', DATE '2001-02-05', 'masculino', 'Ji-Parana',
        NULL, 'ativo'),
    (4, 'Beatriz Oliveira Costa','39053344705', 'beatriz.costa@email.com',
        '(69) 99999-1004', DATE '1987-11-30', 'feminino', 'Porto Velho',
        'Acompanhamento quinzenal.', 'ativo'),
    (5, 'Rafael Nunes Pereira',  '86288307742', 'rafael.pereira@email.com',
        '(69) 99999-1005', DATE '2010-06-15', 'masculino', 'Cacoal',
        'Paciente adolescente; responsavel: Sandra Nunes.', 'ativo');

-- ----------------------------------------------------------------------------
-- Consultas (datas relativas a data atual)
-- ----------------------------------------------------------------------------
INSERT INTO consultas (id_consulta, id_paciente, id_psicologo, data_hora,
                       duracao_minutos, modalidade, status, valor, observacoes)
VALUES
    (1, 1, 1,
        date_trunc('day', now()) - INTERVAL '12 days' + INTERVAL '14 hours',
        50, 'presencial', 'realizada', 180.00, 'Primeira sessao de avaliacao.'),
    (2, 2, 2,
        date_trunc('day', now()) - INTERVAL '9 days' + INTERVAL '10 hours',
        50, 'online', 'realizada', 200.00, 'Sessao realizada por videochamada.'),
    (3, 1, 1,
        date_trunc('day', now()) - INTERVAL '4 days' + INTERVAL '15 hours',
        50, 'presencial', 'realizada', 180.00, 'Continuidade do acompanhamento.'),
    (4, 3, 3,
        date_trunc('day', now()) + INTERVAL '2 days' + INTERVAL '9 hours',
        60, 'presencial', 'agendada', 220.00, 'Avaliacao neuropsicologica.'),
    (5, 4, 2,
        date_trunc('day', now()) + INTERVAL '3 days' + INTERVAL '16 hours',
        50, 'online', 'agendada', 200.00, NULL),
    (6, 2, 3,
        date_trunc('day', now()) - INTERVAL '20 days' + INTERVAL '11 hours',
        50, 'presencial', 'cancelada', 220.00, 'Cancelada pelo paciente.'),
    (7, 5, 1,
        date_trunc('day', now()) + INTERVAL '5 days' + INTERVAL '17 hours',
        50, 'presencial', 'agendada', 180.00, 'Primeira consulta do adolescente.');

-- ----------------------------------------------------------------------------
-- Evolucoes (prontuario)
-- ----------------------------------------------------------------------------
INSERT INTO evolucoes (id_consulta, humor, relato, encaminhamento)
VALUES
    (1, 6, 'Paciente relatou ansiedade no trabalho e dificuldade para dormir. Foram trabalhadas tecnicas de respiracao.',
        'Praticar exercicios de respiracao diariamente.'),
    (2, 7, 'Boa adesao ao tratamento. Paciente identificou situacoes que despertam preocupacao excessiva.',
        NULL),
    (3, 8, 'Evolucao positiva. Paciente relata melhora no sono e maior controle da ansiedade.',
        'Manter sessoes semanais.');

-- ----------------------------------------------------------------------------
-- Ajuste das sequencias apos insercao com ids fixos
-- ----------------------------------------------------------------------------
SELECT setval(pg_get_serial_sequence('psicologos', 'id_psicologo'),
              (SELECT MAX(id_psicologo) FROM psicologos));
SELECT setval(pg_get_serial_sequence('pacientes', 'id_paciente'),
              (SELECT MAX(id_paciente) FROM pacientes));
SELECT setval(pg_get_serial_sequence('consultas', 'id_consulta'),
              (SELECT MAX(id_consulta) FROM consultas));
SELECT setval(pg_get_serial_sequence('evolucoes', 'id_evolucao'),
              (SELECT MAX(id_evolucao) FROM evolucoes));
