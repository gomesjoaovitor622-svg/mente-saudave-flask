"""
============================================================================
Camada de acesso ao banco de dados PostgreSQL - Mente Saudavel
============================================================================
Todo o SQL da aplicacao passa por este modulo. As rotas nunca abrem conexao
diretamente, o que garante:

* uma unica conexao por requisicao (guardada em ``flask.g``);
* fechamento garantido no ``teardown_appcontext``;
* uso de ``RealDictCursor`` (linhas viram dicionarios, prontos para JSON);
* parametros sempre passados via ``%s``/``%(nome)s`` (protecao contra SQL
  injection, pois o psycopg2 faz o escaping no servidor);
* chamada padronizada de stored procedures com ``OUT`` e casts explicitos.
============================================================================
"""

import psycopg2
import psycopg2.extras
from flask import current_app, g


def get_conn():
    """Abre (uma vez por requisicao) a conexao e guarda em ``flask.g``.

    POR QUE REUTILIZAR: abrir uma conexao TCP + autenticacao a cada query e
    caro. ``flask.g`` dura apenas a requisicao, entao nao ha conexao global
    compartilhada entre usuarios (o que seria inseguro em concorrencia).
    """
    if "db_conn" not in g or g.db_conn.closed:
        g.db_conn = psycopg2.connect(
            cursor_factory=psycopg2.extras.RealDictCursor,
            **current_app.config["DB_PARAMS"],
        )
    return g.db_conn


def close_conn(exception=None):
    """Fecha a conexao ao final de cada requisicao (mesmo com excecao).

    O ``pop`` remove a referencia de ``g``; se a conexao ainda estiver aberta,
    e fechada. Isso evita que o pool do PostgreSQL fique saturado.
    """
    conn = g.pop("db_conn", None)
    if conn is not None and not conn.closed:
        conn.close()


def query_all(sql: str, params: tuple | list = ()) -> list[dict]:
    """Executa um SELECT e devolve todas as linhas como dicionarios.

    ``with get_conn() as conn`` gerencia a transacao: commit automatico em caso
    de sucesso e rollback em caso de excecao (comportamento do psycopg2).
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


def query_one(sql: str, params: tuple | list = ()) -> dict | None:
    """Executa um SELECT e devolve a primeira linha (ou ``None``).

    Usado em buscas por id, ``COUNT(*)`` e ``RETURNING`` de INSERT/UPDATE.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None


def execute(sql: str, params: tuple | list = ()) -> int:
    """Executa INSERT/UPDATE/DELETE e devolve o numero de linhas afetadas.

    O retorno permite diferenciar "nao encontrado" (0 linhas) de sucesso sem
    fazer um SELECT extra antes do DELETE.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount


def call_procedure(
    procedure: str,
    in_params: tuple | list,
    casts: list[str] | None = None,
    out_count: int = 2,
) -> dict:
    """Chama uma stored procedure com parametros de entrada e saida.

    O PostgreSQL devolve os parametros ``OUT`` como uma linha de resultado,
    por isso usamos ``fetchone`` apos o ``CALL``. Os ``casts`` deixam os tipos
    explicitos, evitando ambiguidade de sobrecarga (ex.: ``timestamp`` x
    ``timestamptz``) e garantindo que o Postgres escolha a assinatura correta.

    Exemplo gerado para ``sp_criar_paciente``::

        CALL sp_criar_paciente(%s::varchar, %s::varchar, ..., NULL, NULL)

    Os dois ultimos ``NULL`` correspondem aos parametros ``OUT``
    (``p_id_paciente`` e ``p_mensagem``), preenchidos pelo banco.

    Retorno
    -------
    dict
        Ex.: ``{"p_id_paciente": 12, "p_mensagem": "Paciente ... cadastrado"}``.
        Em erro de negocio, o id vem ``None`` e a mensagem explica o motivo.
    """
    if casts:
        placeholders = ", ".join(f"%s::{cast}" for cast in casts)
    else:
        placeholders = ", ".join(["%s"] * len(in_params))

    # As procedures do projeto possuem sempre 2 parametros OUT. Passamos NULL
    # neles porque o valor real e devolvido pelo banco no result set do CALL.
    placeholders += ", " + ", ".join(["NULL"] * out_count)
    params = list(in_params)

    with get_conn() as conn:
        with conn.cursor() as cur:
            # ``procedure`` e uma constante definida no codigo (nunca vem do
            # usuario), portanto a interpolacao do nome e segura; os valores
            # continuam parametrizados.
            cur.execute(f"CALL {procedure}({placeholders})", params)
            row = cur.fetchone()
            return dict(row) if row else {}
