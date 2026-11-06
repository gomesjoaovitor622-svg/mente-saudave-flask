"""Configuracao centralizada da aplicacao.

Todas as variaveis de ambiente ficam neste arquivo (requisito da atividade).
Os valores sao carregados do arquivo ``.env`` (veja ``.env.example``).
"""

import os

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# Carrega o .env da raiz do projeto, sem sobrescrever variaveis do sistema.
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Configuracao base, utilizada em desenvolvimento."""

    # --- Flask -----------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "chave-de-desenvolvimento")
    DEBUG = _as_bool(os.getenv("FLASK_DEBUG"), default=True)
    JSON_SORT_KEYS = False

    # --- Banco de dados --------------------------------------------------
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "mente_saudavel")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))

    # --- Paginacao -------------------------------------------------------
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100

    # --- Regras de negocio ----------------------------------------------
    MIN_PATIENT_AGE = 5

    @classmethod
    def db_params(cls) -> dict:
        """Monta o dicionario de conexao usado pelo psycopg2."""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "dbname": cls.DB_NAME,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
            "connect_timeout": cls.DB_CONNECT_TIMEOUT,
        }


class TestingConfig(Config):
    """Configuracao usada pelos testes automatizados."""

    TESTING = True
    DEBUG = False
    DB_NAME = os.getenv("TEST_DB_NAME", Config.DB_NAME + "_test")


class ProductionConfig(Config):
    """Configuracao de producao: sem debug e chave obrigatoria."""

    DEBUG = False

    def __init__(self) -> None:
        if not os.getenv("SECRET_KEY"):
            raise RuntimeError("Defina SECRET_KEY no ambiente de producao.")
