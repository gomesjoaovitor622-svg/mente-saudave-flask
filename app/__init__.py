"""
============================================================================
Fabrica (Application Factory) da aplicacao Flask - Mente Saudavel
============================================================================
Este modulo concentra a criacao da aplicacao e as decisoes de arquitetura
transversais:

1. ``ApiJSONProvider`` - ensina o Flask a serializar ``date``, ``datetime``,
   ``Decimal`` (tipos devolvidos pelo PostgreSQL/psycopg2) e ``set``. Sem isso,
   um ``SELECT`` com ``NUMERIC`` ou ``TIMESTAMPTZ`` quebraria a resposta JSON.
2. ``create_app`` - recebe uma classe de configuracao (dev, test ou prod),
   registra blueprints, handlers de erro, CORS e o fechamento da conexao.
3. CORS - permite que o painel, o Postman e aplicativos moveis consumam a API
   sem bloqueio de origem cruzada (requisito de integracao).
4. ``teardown_appcontext`` - garante que a conexao com o banco seja fechada
   ao final de CADA requisicao, evitando vazamento de conexoes.

POR QUE SEPARAR EM BLUEPRINTS?
------------------------------
Cada dominio (pacientes, psicologos, consultas, evolucoes, relatorios) fica
em seu proprio modulo. Isso reduz o acoplamento, facilita testes e permite
que a equipe trabalhe em arquivos diferentes sem conflito.
============================================================================
"""

from datetime import date, datetime
from decimal import Decimal

from flask import Flask, render_template, request
from flask.json.provider import DefaultJSONProvider

from .config import Config
from .db import close_conn
from .errors import register_error_handlers
from .routes import register_blueprints


class ApiJSONProvider(DefaultJSONProvider):
    """Serializa tipos do PostgreSQL que o JSON nativo nao conhece.

    * ``date``/``datetime`` -> string ISO 8601 (ex.: ``2026-11-20T14:30:00``);
    * ``Decimal`` -> ``float`` (valores monetarios e medias);
    * ``set`` -> lista ordenada (estabilidade na comparacao de respostas).

    O ``ensure_ascii = False`` (configurado em ``create_app``) preserva
    acentos no JSON, melhorando a legibilidade das respostas em portugues.
    """

    @staticmethod
    def default(value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, set):
            return sorted(value)
        return DefaultJSONProvider.default(value)


def create_app(config_class=Config) -> Flask:
    """Cria e configura uma instancia da API.

    Parametros
    ----------
    config_class : type
        Classe de configuracao (``Config``, ``TestingConfig`` ou
        ``ProductionConfig``). Injetar a configuracao facilita os testes:
        a suite usa um banco separado (``mente_saudavel_test``) sem tocar
        nos dados de desenvolvimento.

    Retorno
    -------
    Flask
        Aplicacao pronta para ser servida por ``app.run`` ou por um WSGI.
    """
    # ``static_folder``/``template_folder`` explicitos deixam claro onde estao
    # o painel web (HTML/CSS/JS) e facilitam o deploy em outro servidor.
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config_class)

    # ``DB_PARAMS`` e derivado da configuracao e consumido apenas por app/db.py.
    # Centralizar aqui evita que cada rota monte sua propria string de conexao.
    app.config["DB_PARAMS"] = config_class.db_params()

    # Substitui o provider de JSON padrao pelo nosso (datas, Decimal etc.).
    app.json = ApiJSONProvider(app)
    app.json.ensure_ascii = False  # mantem acentos legiveis
    app.json.sort_keys = False     # preserva a ordem definida nas rotas

    # Handlers centralizados: qualquer ApiError, violacao do PostgreSQL ou
    # excecao inesperada vira JSON padronizado (nunca HTML de erro).
    register_error_handlers(app)

    # Blueprints = modulos de rotas (health, pacientes, psicologos, ...).
    register_blueprints(app)

    # Fecha a conexao psycopg2 guardada em ``flask.g`` ao fim da requisicao,
    # mesmo quando ocorre excecao. Evita "too many connections" no Postgres.
    app.teardown_appcontext(close_conn)

    @app.after_request
    def add_cors_headers(response):
        """Adiciona cabecalhos CORS a todas as respostas.

        POR QUE: o painel pode ser servido de outra origem (ex.: tunel
        Cloudflare, Live Server) e o Postman/browser precisa conseguir ler a
        resposta. ``OPTIONS`` e respondido com 204 para o pre-flight.
        """
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        return response

    @app.before_request
    def handle_preflight():
        """Responde ao pre-flight CORS (OPTIONS) antes de qualquer rota.

        O Flask adiciona OPTIONS automaticamente as rotas e devolveria 200;
        interceptar aqui garante o 204 padrao para pre-flight e evita executar
        consultas ao banco durante o OPTIONS.
        """
        if request.method == "OPTIONS":
            return "", 204

    @app.route("/api/<path:_path>", methods=["OPTIONS"])
    def api_options(_path):
        """Rota de fallback para OPTIONS em qualquer caminho /api/*."""
        return "", 204

    @app.get("/")
    def index():
        """Entrega o painel web (Jinja) que consome a propria API via fetch."""
        return render_template("index.html")

    return app
