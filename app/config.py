"""
============================================================================
Configuracao centralizada da aplicacao - Mente Saudavel
============================================================================
Todas as variaveis de ambiente ficam neste arquivo (requisito da atividade).
Os valores sao carregados do arquivo ``.env`` (veja ``.env.example``) e podem
ser sobrescritos por variaveis do sistema operacional.

POR QUE NAO COLOCAR CREDENCIAIS NO CODIGO?
------------------------------------------
O repositorio e publico. Senhas no codigo vazam para o GitHub e para qualquer
pessoa com acesso ao ZIP. Com ``os.getenv`` + ``.env`` (ignorado pelo Git),
cada ambiente informa suas proprias credenciais.
============================================================================
"""

import os

from dotenv import load_dotenv

# Raiz do projeto (um nivel acima de app/), usada para localizar o .env.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# Carrega o .env da raiz sem sobrescrever variaveis ja definidas no sistema.
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _as_bool(value: str | None, default: bool = False) -> bool:
    """Converte texto de ambiente em booleano de forma tolerante.

    Aceita ``1/true/yes/on`` (qualquer caixa) e trata ``None`` com o padrao.
    Evita o erro classico de ``bool("false") == True``.
    """
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Configuracao da aplicacao, lida do ambiente (``.env``)."""

    # --- Flask -----------------------------------------------------------
    DEBUG = _as_bool(os.getenv("FLASK_DEBUG"), default=True)
    JSON_SORT_KEYS = False

    # --- Banco de dados --------------------------------------------------
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "mente_saudavel")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    # Timeout curto evita que uma requisicao fique pendurada se o banco cair.
    DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))

    # --- Paginacao -------------------------------------------------------
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100  # teto de seguranca contra ?per_page=1000000

    @classmethod
    def db_params(cls) -> dict:
        """Monta o dicionario de conexao usado pelo psycopg2.

        Manter os nomes no formato esperado pelo driver (``dbname``, ``host``,
        ``port``...) evita concatenar strings de conexao e previne erros de
        escaping com senhas que contenham caracteres especiais.
        """
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "dbname": cls.DB_NAME,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
            "connect_timeout": cls.DB_CONNECT_TIMEOUT,
        }
