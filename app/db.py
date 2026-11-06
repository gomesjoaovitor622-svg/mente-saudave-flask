"""Camada de acesso ao banco de dados PostgreSQL."""

import psycopg2
import psycopg2.extras
from flask import current_app, g


def get_conn():
    """Abre (uma vez por requisicao) a conexao e guarda em ``flask.g``."""
    if "db_conn" not in g or g.db_conn.closed:
        g.db_conn = psycopg2.connect(
            cursor_factory=psycopg2.extras.RealDictCursor,
            **current_app.config["DB_PARAMS"],
        )
    return g.db_conn


def close_conn(exception=None):
    """Fecha a conexao ao final de cada requisicao."""
    conn = g.pop("db_conn", None)
    if conn is not None and not conn.closed:
        conn.close()


def query_all(sql: str, params: tuple | list = ()) -> list[dict]:
    """Executa um SELECT e devolve todas as linhas como dicionarios."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


def query_one(sql: str, params: tuple | list = ()) -> dict | None:
    """Executa um SELECT e devolve a primeira linha (ou None)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None


def execute(sql: str, params: tuple | list = ()) -> int:
    """Executa INSERT/UPDATE/DELETE e devolve o numero de linhas afetadas."""
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
    explicitos, evitando ambiguidade de sobrecarga (ex.: timestamp x
    timestamptz).
    """
    if casts:
        placeholders = ", ".join(f"%s::{cast}" for cast in casts)
    else:
        placeholders = ", ".join(["%s"] * len(in_params))
    placeholders += ", " + ", ".join(["NULL"] * out_count)
    params = list(in_params)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"CALL {procedure}({placeholders})", params)
            row = cur.fetchone()
            return dict(row) if row else {}
