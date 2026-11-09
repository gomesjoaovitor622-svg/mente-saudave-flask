"""
============================================================================
Testes de integridade do BANCO DE DADOS - Mente Saudavel
============================================================================
Objetivo: provar que as CHECK constraints, chaves estrangeiras, UNIQUE,
indice unico parcial, triggers e stored procedures rejeitam dados invalidos
MESMO quando a API e ignorada (acesso direto via psycopg2).

Execute com o banco de teste configurado:

    set RUN_DB_TESTS=1
    set TEST_DB_NAME=mente_saudavel_test
    set DB_HOST=127.0.0.1
    set DB_PORT=55432
    set DB_USER=postgres
    set DB_PASSWORD=postgres
    pytest tests/test_constraints.py -q

Cada teste roda em uma transacao e faz ROLLBACK no final, portanto nao deixa
lixo no banco. Violacoes esperadas usam SAVEPOINT para nao abortar a transacao
inteira.
============================================================================
"""

import os
import random
from contextlib import contextmanager

import psycopg2
import pytest
from psycopg2 import errors

from app.config import TestingConfig

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Defina RUN_DB_TESTS=1 e um banco de teste para executar.",
)


def _cpf_valido() -> str:
    """Gera um CPF valido aleatorio (para evitar conflito entre execucoes)."""
    base = [random.randint(0, 9) for _ in range(9)]
    for position in (9, 10):
        total = sum(base[index] * ((position + 1) - index) for index in range(position))
        digit = (total * 10) % 11
        base.append(0 if digit == 10 else digit)
    return "".join(map(str, base))


@pytest.fixture()
def conn():
    """Conexao direta com o banco de teste (sem passar pela API)."""
    connection = psycopg2.connect(**TestingConfig.db_params())
    connection.autocommit = False
    yield connection
    connection.rollback()
    connection.close()


@contextmanager
def expect_db_error(conn, error_type):
    """Executa um bloco esperando uma excecao do PostgreSQL.

    Usa SAVEPOINT para que a transacao continue utilizavel depois do erro,
    permitindo validar varias constraints no mesmo teste.
    """
    with conn.cursor() as cur:
        cur.execute("SAVEPOINT teste_constraint")
    try:
        yield
    except error_type:
        with conn.cursor() as cur:
            cur.execute("ROLLBACK TO SAVEPOINT teste_constraint")
    else:
        raise AssertionError(f"Esperava {error_type.__name__}, mas o comando passou.")
    finally:
        with conn.cursor() as cur:
            cur.execute("RELEASE SAVEPOINT teste_constraint")


def _novo_paciente(conn, **overrides):
    """Insere um paciente valido e devolve o id gerado."""
    cpf = overrides.pop("cpf", _cpf_valido())
    email = overrides.pop("email", f"teste.{cpf}@email.com")
    dados = {
        "nome": "Paciente Teste Constraint",
        "cpf": cpf,
        "email": email,
        "data_nascimento": "1995-04-12",
        "genero": "nao_informado",
        **overrides,
    }
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pacientes (nome, cpf, email, data_nascimento, genero)
            VALUES (%(nome)s, %(cpf)s, %(email)s, %(data_nascimento)s, %(genero)s)
            RETURNING id_paciente
            """,
            dados,
        )
        return cur.fetchone()[0]


def _novo_psicologo(conn, **overrides):
    """Insere um psicologo valido e devolve o id gerado."""
    sufixo = random.randint(10000, 99999)
    dados = {
        "nome": f"Psicologo Teste {sufixo}",
        "crp": f"06/{sufixo}",
        "email": f"psi.{sufixo}@email.com",
        "especialidade": "Terapia Cognitivo-Comportamental",
        "valor_sessao": 180.00,
        **overrides,
    }
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO psicologos (nome, crp, email, especialidade, valor_sessao)
            VALUES (%(nome)s, %(crp)s, %(email)s, %(especialidade)s, %(valor_sessao)s)
            RETURNING id_psicologo
            """,
            dados,
        )
        return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# 1. CHECK CONSTRAINTS (o edital exige no minimo 3; o projeto possui 20+)
# ---------------------------------------------------------------------------
def test_check_cpf_formato(conn):
    """CPF com letras/menos de 11 digitos deve ser rejeitado."""
    with expect_db_error(conn, errors.CheckViolation):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pacientes (nome, cpf, email, data_nascimento)
                VALUES ('Teste CPF', 'abc123', 'cpf@invalido.com', '1990-01-01')
                """
            )


def test_check_data_nascimento_futura(conn):
    """Data de nascimento no futuro viola ck_pacientes_nascimento."""
    with expect_db_error(conn, errors.CheckViolation):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pacientes (nome, cpf, email, data_nascimento)
                VALUES ('Teste Futuro', %s, %s, CURRENT_DATE + 1)
                """,
                (_cpf_valido(), f"futuro.{random.randint(1, 99999)}@email.com"),
            )


def test_check_genero_dominio(conn):
    """Genero fora do dominio viola ck_pacientes_genero."""
    with expect_db_error(conn, errors.CheckViolation):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pacientes (nome, cpf, email, data_nascimento, genero)
                VALUES ('Teste Genero', %s, %s, '1990-01-01', 'invalido')
                """,
                (_cpf_valido(), f"genero.{random.randint(1, 99999)}@email.com"),
            )


def test_check_duracao_consulta(conn):
    """Duracao fora de 15..180 viola ck_consultas_duracao."""
    paciente = _novo_paciente(conn)
    psicologo = _novo_psicologo(conn)
    with expect_db_error(conn, errors.CheckViolation):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO consultas (id_paciente, id_psicologo, data_hora, duracao_minutos)
                VALUES (%s, %s, now() + interval '10 days', 10)
                """,
                (paciente, psicologo),
            )


def test_check_modalidade_consulta(conn):
    """Modalidade invalida viola ck_consultas_modalidade."""
    paciente = _novo_paciente(conn)
    psicologo = _novo_psicologo(conn)
    with expect_db_error(conn, errors.CheckViolation):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO consultas (id_paciente, id_psicologo, data_hora, modalidade)
                VALUES (%s, %s, now() + interval '11 days', 'domiciliar')
                """,
                (paciente, psicologo),
            )


def test_check_humor_evolucao(conn):
    """Humor fora de 1..10 viola ck_evolucoes_humor."""
    paciente = _novo_paciente(conn)
    psicologo = _novo_psicologo(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO consultas (id_paciente, id_psicologo, data_hora, status)
            VALUES (%s, %s, now() + interval '12 days', 'realizada')
            RETURNING id_consulta
            """,
            (paciente, psicologo),
        )
        consulta = cur.fetchone()[0]
    with expect_db_error(conn, errors.CheckViolation):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO evolucoes (id_consulta, humor, relato)
                VALUES (%s, 11, 'Relato valido com mais de dez caracteres.')
                """,
                (consulta,),
            )


def test_check_relato_minimo(conn):
    """Relato com menos de 10 caracteres viola ck_evolucoes_relato_minimo."""
    paciente = _novo_paciente(conn)
    psicologo = _novo_psicologo(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO consultas (id_paciente, id_psicologo, data_hora, status)
            VALUES (%s, %s, now() + interval '13 days', 'realizada')
            RETURNING id_consulta
            """,
            (paciente, psicologo),
        )
        consulta = cur.fetchone()[0]
    with expect_db_error(conn, errors.CheckViolation):
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO evolucoes (id_consulta, humor, relato) VALUES (%s, 5, 'curto')",
                (consulta,),
            )


def test_check_valor_sessao_positivo(conn):
    """valor_sessao <= 0 viola ck_psicologos_valor_positivo."""
    with expect_db_error(conn, errors.CheckViolation):
        _novo_psicologo(conn, valor_sessao=0)


# ---------------------------------------------------------------------------
# 2. UNIQUE e integridade referencial
# ---------------------------------------------------------------------------
def test_unique_cpf_paciente(conn):
    """Dois pacientes com o mesmo CPF violam a UNIQUE."""
    cpf = _cpf_valido()
    _novo_paciente(conn, cpf=cpf, email=f"a.{cpf}@email.com")
    with expect_db_error(conn, errors.UniqueViolation):
        _novo_paciente(conn, cpf=cpf, email=f"b.{cpf}@email.com")


def test_unique_email_paciente(conn):
    """Dois pacientes com o mesmo e-mail violam a UNIQUE."""
    email = f"duplicado.{random.randint(1, 99999)}@email.com"
    _novo_paciente(conn, email=email)
    with expect_db_error(conn, errors.UniqueViolation):
        _novo_paciente(conn, email=email)


def test_unique_crp_psicologo(conn):
    """Dois psicologos com o mesmo CRP violam a UNIQUE."""
    crp = f"06/{random.randint(10000, 99999)}"
    _novo_psicologo(conn, crp=crp)
    with expect_db_error(conn, errors.UniqueViolation):
        _novo_psicologo(conn, crp=crp)


def test_fk_paciente_inexistente(conn):
    """Consulta com paciente inexistente viola a FK."""
    psicologo = _novo_psicologo(conn)
    with expect_db_error(conn, errors.ForeignKeyViolation):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO consultas (id_paciente, id_psicologo, data_hora)
                VALUES (999999, %s, now() + interval '20 days')
                """,
                (psicologo,),
            )


def test_fk_restrict_psicologo_com_consulta(conn):
    """Excluir psicologo com consultas deve ser bloqueado (RESTRICT)."""
    paciente = _novo_paciente(conn)
    psicologo = _novo_psicologo(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO consultas (id_paciente, id_psicologo, data_hora)
            VALUES (%s, %s, now() + interval '21 days')
            """,
            (paciente, psicologo),
        )
    # O PostgreSQL usa RestrictViolation (subclasse de IntegrityError) quando
    # a FK foi declarada com ON DELETE RESTRICT.
    with expect_db_error(conn, (errors.ForeignKeyViolation, errors.RestrictViolation)):
        with conn.cursor() as cur:
            cur.execute("DELETE FROM psicologos WHERE id_psicologo = %s", (psicologo,))


def test_cascade_paciente_remove_consultas_e_evolucoes(conn):
    """ON DELETE CASCADE remove consultas e evolucoes do paciente."""
    paciente = _novo_paciente(conn)
    psicologo = _novo_psicologo(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO consultas (id_paciente, id_psicologo, data_hora, status)
            VALUES (%s, %s, now() + interval '22 days', 'realizada')
            RETURNING id_consulta
            """,
            (paciente, psicologo),
        )
        consulta = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO evolucoes (id_consulta, humor, relato)
            VALUES (%s, 7, 'Relato valido para o teste de cascade.')
            """,
            (consulta,),
        )
        cur.execute("DELETE FROM pacientes WHERE id_paciente = %s", (paciente,))
        cur.execute("SELECT COUNT(*) FROM consultas WHERE id_paciente = %s", (paciente,))
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT COUNT(*) FROM evolucoes WHERE id_consulta = %s", (consulta,))
        assert cur.fetchone()[0] == 0


# ---------------------------------------------------------------------------
# 3. Indice unico parcial anti-double-booking
# ---------------------------------------------------------------------------
def test_agenda_impede_double_booking(conn):
    """Dois agendamentos ativos no mesmo horario/psicologo violam o indice."""
    paciente = _novo_paciente(conn)
    psicologo = _novo_psicologo(conn)
    horario = "now() + interval '30 days'"
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO consultas (id_paciente, id_psicologo, data_hora)
            VALUES (%s, %s, {horario})
            """,
            (paciente, psicologo),
        )
    with expect_db_error(conn, errors.UniqueViolation):
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO consultas (id_paciente, id_psicologo, data_hora)
                VALUES (%s, %s, {horario})
                """,
                (paciente, psicologo),
            )


def test_agenda_permite_reutilizar_horario_cancelado(conn):
    """Consulta cancelada libera o horario para um novo agendamento."""
    paciente = _novo_paciente(conn)
    psicologo = _novo_psicologo(conn)
    horario = "now() + interval '31 days'"
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO consultas (id_paciente, id_psicologo, data_hora, status)
            VALUES (%s, %s, {horario}, 'cancelada')
            """,
            (paciente, psicologo),
        )
        cur.execute(
            f"""
            INSERT INTO consultas (id_paciente, id_psicologo, data_hora)
            VALUES (%s, %s, {horario})
            """,
            (paciente, psicologo),
        )
        cur.execute(
            "SELECT COUNT(*) FROM consultas WHERE id_psicologo = %s "
            "AND data_hora = now() + interval '31 days'",
            (psicologo,),
        )
        assert cur.fetchone()[0] == 2


# ---------------------------------------------------------------------------
# 4. Triggers (auditoria e timestamp)
# ---------------------------------------------------------------------------
def test_trigger_auditoria_insert_update_delete(conn):
    """A trigger deve registrar INSERT, UPDATE e DELETE em auditoria_pacientes."""
    paciente = _novo_paciente(conn, nome="Paciente Auditoria")
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE pacientes SET nome = 'Paciente Auditado' WHERE id_paciente = %s",
            (paciente,),
        )
        cur.execute("DELETE FROM pacientes WHERE id_paciente = %s", (paciente,))
        cur.execute(
            """
            SELECT operacao FROM auditoria_pacientes
             WHERE id_paciente = %s
             ORDER BY id_auditoria
            """,
            (paciente,),
        )
        operacoes = [row[0] for row in cur.fetchall()]
    assert operacoes == ["INSERT", "UPDATE", "DELETE"]


def test_trigger_atualiza_timestamp(conn):
    """A trigger BEFORE UPDATE deve preencher atualizado_em."""
    paciente = _novo_paciente(conn)
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE pacientes SET cidade = 'Cacoal' WHERE id_paciente = %s",
            (paciente,),
        )
        cur.execute(
            "SELECT atualizado_em IS NOT NULL FROM pacientes WHERE id_paciente = %s",
            (paciente,),
        )
        assert cur.fetchone()[0] is True


# ---------------------------------------------------------------------------
# 5. Stored procedures (regras de negocio no banco)
# ---------------------------------------------------------------------------
def test_sp_criar_paciente_sucesso(conn):
    """sp_criar_paciente devolve id e mensagem de sucesso."""
    cpf = _cpf_valido()
    with conn.cursor() as cur:
        cur.execute(
            """
            CALL sp_criar_paciente(
                'Paciente Procedure', %s, %s, NULL, DATE '1990-01-01',
                'nao_informado', 'Porto Velho', NULL, NULL, NULL
            )
            """,
            (cpf, f"proc.{cpf}@email.com"),
        )
        row = cur.fetchone()
    assert row[0] is not None
    assert "sucesso" in row[1].lower()


def test_sp_criar_paciente_cpf_duplicado(conn):
    """CPF duplicado retorna id NULL e mensagem de negocio."""
    cpf = _cpf_valido()
    _novo_paciente(conn, cpf=cpf, email=f"dup.{cpf}@email.com")
    with conn.cursor() as cur:
        cur.execute(
            """
            CALL sp_criar_paciente(
                'Outro Paciente', %s, %s, NULL, DATE '1990-01-01',
                'nao_informado', NULL, NULL, NULL, NULL
            )
            """,
            (cpf, f"outro.{cpf}@email.com"),
        )
        row = cur.fetchone()
    assert row[0] is None
    assert "CPF" in row[1]


def test_sp_criar_paciente_idade_minima(conn):
    """Paciente com menos de 5 anos retorna erro de negocio."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CALL sp_criar_paciente(
                'Bebe Teste', %s, %s, NULL, (CURRENT_DATE - INTERVAL '1 year')::date,
                'nao_informado', NULL, NULL, NULL, NULL
            )
            """,
            (_cpf_valido(), f"bebe.{random.randint(1, 99999)}@email.com"),
        )
        row = cur.fetchone()
    assert row[0] is None
    assert "5 anos" in row[1]


def test_sp_agendar_consulta_conflito(conn):
    """Segundo agendamento ativo no mesmo horario retorna erro de negocio."""
    paciente = _novo_paciente(conn)
    psicologo = _novo_psicologo(conn)
    horario = "now() + interval '40 days'"
    with conn.cursor() as cur:
        cur.execute(
            f"""
            CALL sp_agendar_consulta(
                %s, %s, {horario}, 50::smallint, 'presencial'::varchar,
                NULL::numeric, NULL::text, NULL, NULL
            )
            """,
            (paciente, psicologo),
        )
        first = cur.fetchone()
        cur.execute(
            f"""
            CALL sp_agendar_consulta(
                %s, %s, {horario}, 50::smallint, 'presencial'::varchar,
                NULL::numeric, NULL::text, NULL, NULL
            )
            """,
            (paciente, psicologo),
        )
        second = cur.fetchone()
    assert first[0] is not None
    assert second[0] is None
    assert "ocupado" in second[1].lower()


def test_sp_registrar_evolucao_duplicada(conn):
    """Segunda evolucao para a mesma consulta retorna erro de negocio."""
    paciente = _novo_paciente(conn)
    psicologo = _novo_psicologo(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO consultas (id_paciente, id_psicologo, data_hora, status)
            VALUES (%s, %s, now() + interval '41 days', 'realizada')
            RETURNING id_consulta
            """,
            (paciente, psicologo),
        )
        consulta = cur.fetchone()[0]
        cur.execute(
            """
            CALL sp_registrar_evolucao(
                %s, 8::smallint, 'Primeiro relato clinico valido.'::text,
                NULL::varchar, NULL, NULL
            )
            """,
            (consulta,),
        )
        first = cur.fetchone()
        cur.execute(
            """
            CALL sp_registrar_evolucao(
                %s, 7::smallint, 'Segundo relato clinico valido.'::text,
                NULL::varchar, NULL, NULL
            )
            """,
            (consulta,),
        )
        second = cur.fetchone()
    assert first[0] is not None
    assert second[0] is None
    assert "ja possui" in second[1].lower()


# ---------------------------------------------------------------------------
# 6. Views e funcoes de relatorio
# ---------------------------------------------------------------------------
def test_views_retornam_joins(conn):
    """As views devem expor os nomes de paciente e psicologo."""
    with conn.cursor() as cur:
        cur.execute("SELECT paciente, psicologo FROM vw_agenda_completa LIMIT 1")
        agenda = cur.fetchone()
        cur.execute("SELECT paciente, psicologo FROM vw_evolucoes LIMIT 1")
        evolucoes = cur.fetchone()
        cur.execute("SELECT paciente, psicologo FROM vw_relatorio_atendimentos LIMIT 1")
        relatorio = cur.fetchone()
    assert agenda and agenda[0] and agenda[1]
    assert evolucoes and evolucoes[0] and evolucoes[1]
    assert relatorio and relatorio[0] and relatorio[1]


def test_fn_relatorio_atendimentos(conn):
    """A funcao tabular deve devolver as consultas do periodo."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM fn_relatorio_atendimentos(DATE '2000-01-01', DATE '2100-12-31')"
        )
        assert cur.fetchone()[0] > 0


def test_fn_resumo_paciente(conn):
    """O resumo deve trazer os totais do paciente."""
    with conn.cursor() as cur:
        cur.execute("SELECT id_paciente FROM pacientes ORDER BY id_paciente LIMIT 1")
        paciente = cur.fetchone()[0]
        cur.execute("SELECT * FROM fn_resumo_paciente(%s)", (paciente,))
        row = cur.fetchone()
    assert row is not None
    assert row[0] == paciente
