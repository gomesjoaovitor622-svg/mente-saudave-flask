"""Fabrica (factory) da aplicacao Flask."""

from datetime import date, datetime
from decimal import Decimal

from flask import Flask, render_template
from flask.json.provider import DefaultJSONProvider

from .config import Config
from .db import close_conn
from .errors import register_error_handlers
from .routes import register_blueprints


class ApiJSONProvider(DefaultJSONProvider):
    """Serializa datas e valores numericos do PostgreSQL para JSON."""

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
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config_class)
    app.config["DB_PARAMS"] = config_class.db_params()

    app.json = ApiJSONProvider(app)
    app.json.ensure_ascii = False
    app.json.sort_keys = False

    register_error_handlers(app)
    register_blueprints(app)
    app.teardown_appcontext(close_conn)

    @app.after_request
    def add_cors_headers(response):
        """Permite que frontends e aplicativos moveis consumam a API."""
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    @app.route("/api/<path:_path>", methods=["OPTIONS"])
    def api_options(_path):
        return "", 204

    @app.get("/")
    def index():
        return render_template("index.html")

    return app
