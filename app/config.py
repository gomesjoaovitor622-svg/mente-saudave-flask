"""
============================================================================
Configuracao centralizada da aplicacao - Mente Saudavel
============================================================================
Todas as variaveis de ambiente ficam neste arquivo (requisito da atividade).
Os valores sao carregados do arquivo ``.env`` (veja ``.env.example``) e podem
ser sobrescritos por variaveis do sistema operacional - util em producao.

POR QUE NAO COLOCAR CREDENCIAIS NO CODIGO?
------------------------------------------
O repositorio e publico. Senhas e chaves no codigo vazam para o GitHub e para
qualquer pessoa com acesso ao ZIP. Com ``os.getenv`` + ``.env`` (ignorado pelo
Git), cada ambiente informa suas proprias credenciais.

CLASSES DE CONFIGURACAO
-----------------------
* ``Config``          -> desenvolvimento local (valores padrao seguros).
* ``TestingConfig``   -> pytest, aponta para ``mente_saudavel_test``.
* ``ProductionConfig``-> sem debug e com ``SECRET_KEY`` obrigatoria.
============================================================================
"""

import os

from dotenv import load_dotenv

# Raiz do projeto (um nivel acima de app/), usada para localizar o .env.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# Carrega o .env da raiz sem sobrescrever variaveis ja definidas no sistema.
# Assim, ``DB_HOST=... python app.py`` tem prioridade sobre o arquivo.
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _as_bool(value: str | None, default: bool = False) -> bool:
    """Converte texto de ambiente em booleano de forma tolerante.

    Aceita ``1/true/yes/on`` (qualquer caixa) e trata ``None`` com o padrao.
    Evita o erro classico de ``bool("false") == True``.
    """
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_list(value: str | None, default: list[str]) -> list[str]:
    """Converte uma lista separada por virgulas em ``list[str]``.

    Exemplo: ``CORS_ORIGINS="https://app.exemplo.com, https://admin.exemplo.com"``
    vira ``["https://app.exemplo.com", "https://admin.exemplo.com"]``.
    """
    if value is None or not value.strip():
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


# Valor de desenvolvimento usado quando ninguem definiu SECRET_KEY. E proposital
# que ele seja fraco: ``create_app`` recusa subir em producao com esta chave.
SECRET_KEY_PADRAO = "chave-de-desenvolvimento"


class Config:
    """Configuracao base, utilizada em desenvolvimento."""

    # --- Flask -----------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", SECRET_KEY_PADRAO)
    DEBUG = _as_bool(os.getenv("FLASK_DEBUG"), default=True)
    JSON_SORT_KEYS = False

    # --- CORS ------------------------------------------------------------
    # ``*`` libera qualquer origem, o que e aceitavel apenas em desenvolvimento.
    # Em producao, use ProductionConfig (que nao libera nada por padrao) ou
    # defina CORS_ORIGINS com as origens reais do painel/app.
    CORS_ORIGINS = _as_list(os.getenv("CORS_ORIGINS"), default=["*"])

    # --- Banco de dados --------------------------------------------------
    # Cada valor pode vir do ambiente. Os padroes funcionam no Docker/local.
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

    # --- Regras de negocio ----------------------------------------------
    MIN_PATIENT_AGE = 5  # espelha a regra da procedure sp_criar_paciente

    @classmethod
    def db_params(cls) -> dict:
        """Monta o dicionario de conexao usado pelo psycopg2.

        Manter os nomes no formato esperado pelo driver (``dbname``, ``host``,
        ``port``...) evita concatenar strings de conexao e previne erros de
        escaping com senhas que contenham caracteres especiais.

        Se ``DATABASE_URL`` estiver definida (padrao em hospedagens como Render,
        Railway e Heroku), ela tem prioridade: e uma unica string que ja traz
        host, porta, usuario, senha, banco e ``sslmode``. Assim, o mesmo codigo
        funciona local e na nuvem sem precisar remontar as partes.
        """
        dsn = os.getenv("DATABASE_URL")
        if dsn:
            return {"dsn": dsn, "connect_timeout": cls.DB_CONNECT_TIMEOUT}
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "dbname": cls.DB_NAME,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
            "connect_timeout": cls.DB_CONNECT_TIMEOUT,
        }


class TestingConfig(Config):
    """Configuracao usada pelos testes automatizados.

    Aponta para um banco separado (``TEST_DB_NAME``) para que a suite possa
    inserir, atualizar e excluir registros sem afetar os dados de demonstracao.
    """

    TESTING = True
    DEBUG = False
    DB_NAME = os.getenv("TEST_DB_NAME", Config.DB_NAME + "_test")


class ProductionConfig(Config):
    """Configuracao de producao: sem debug, sem CORS aberto.

    A chave ``SECRET_KEY`` continua vindo do ambiente e e validada na criacao
    da aplicacao (``create_app``): subir em producao com a chave de
    desenvolvimento levanta erro, em vez de expor o app com uma chave publica.

    ``CORS_ORIGINS`` fica vazio por padrao porque o painel e servido pela
    propria aplicacao (mesma origem, sem CORS). Se houver um front-end em outro
    dominio, basta definir ``CORS_ORIGINS=https://meu-painel.com``.
    """

    DEBUG = False
    CORS_ORIGINS = _as_list(os.getenv("CORS_ORIGINS"), default=[])
