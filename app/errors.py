"""Tratamento padronizado de erros da API (sempre em JSON)."""

import logging

import psycopg2
from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Erro de negocio/validacao que vira uma resposta JSON."""

    def __init__(self, message: str, status_code: int = 400, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


def error_response(message: str, status_code: int, details=None):
    payload = {
        "erro": True,
        "mensagem": message,
        "status": status_code,
    }
    if details:
        payload["detalhes"] = details
    return jsonify(payload), status_code


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return error_response(error.message, error.status_code, error.details)

    @app.errorhandler(psycopg2.errors.UniqueViolation)
    def handle_unique_violation(error):
        return error_response("Registro duplicado: valor unico ja cadastrado.", 409)

    @app.errorhandler(psycopg2.errors.ForeignKeyViolation)
    def handle_foreign_key_violation(error):
        return error_response(
            "Operacao bloqueada: existem registros vinculados a este item.", 409
        )

    @app.errorhandler(psycopg2.errors.CheckViolation)
    def handle_check_violation(error):
        return error_response("Dados invalidos segundo as regras do banco.", 422)

    @app.errorhandler(psycopg2.Error)
    def handle_database_error(error):
        logger.exception("Erro de banco de dados")
        return error_response("Erro ao acessar o banco de dados.", 503)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return error_response(error.description, error.code)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.exception("Erro inesperado")
        return error_response("Erro interno do servidor.", 500)
