"""
============================================================================
Tratamento padronizado de erros da API - Mente Saudavel
============================================================================
Toda resposta de erro segue o mesmo contrato JSON::

    {
      "erro": true,
      "mensagem": "texto amigavel",
      "status": 422,
      "detalhes": {"campos": ["cpf"]}      # opcional
    }

POR QUE CENTRALIZAR?
--------------------
* O front-end/Postman trata erro em um unico formato, sem ``try/except`` em
  cada rota.
* Mensagens tecnicas do PostgreSQL nao vazam para o usuario final (seguranca).
* As violacoes de integridade (UNIQUE, FK, CHECK) sao traduzidas em codigos
  HTTP semanticos: 409 para conflito e 422 para dado invalido.
============================================================================
"""

import logging

import psycopg2
from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Erro de negocio/validacao que vira uma resposta JSON.

    As rotas levantam ``ApiError`` quando a regra de negocio falha (ex.:
    paciente nao encontrado, payload invalido). O handler registrado em
    ``register_error_handlers`` transforma a excecao em JSON.
    """

    def __init__(self, message: str, status_code: int = 400, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


def error_response(message: str, status_code: int, details=None):
    """Monta o payload padrao de erro e devolve ``(json, status)``."""
    payload = {
        "erro": True,
        "mensagem": message,
        "status": status_code,
    }
    if details:
        payload["detalhes"] = details
    return jsonify(payload), status_code


def register_error_handlers(app):
    """Registra os handlers globais de erro na aplicacao Flask.

    A ordem importa: excecoes mais especificas (``UniqueViolation``) sao
    tratadas antes do ``psycopg2.Error`` generico.
    """

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        """Erro de negocio levantado intencionalmente pela aplicacao."""
        return error_response(error.message, error.status_code, error.details)

    @app.errorhandler(psycopg2.errors.UniqueViolation)
    def handle_unique_violation(error):
        """UNIQUE/PK duplicada -> HTTP 409 Conflict."""
        return error_response("Registro duplicado: valor unico ja cadastrado.", 409)

    @app.errorhandler(psycopg2.errors.ForeignKeyViolation)
    def handle_foreign_key_violation(error):
        """FK inexistente ou RESTRICT impedindo exclusao -> HTTP 409."""
        return error_response(
            "Operacao bloqueada: existem registros vinculados a este item.", 409
        )

    @app.errorhandler(psycopg2.errors.CheckViolation)
    def handle_check_violation(error):
        """CHECK constraint violada -> HTTP 422 Unprocessable Entity."""
        return error_response("Dados invalidos segundo as regras do banco.", 422)

    @app.errorhandler(psycopg2.Error)
    def handle_database_error(error):
        """Falha de conexao/execucao no banco -> HTTP 503 Service Unavailable.

        O detalhe tecnico vai apenas para o log do servidor; o cliente recebe
        uma mensagem generica para nao expor a estrutura interna.
        """
        logger.exception("Erro de banco de dados")
        return error_response("Erro ao acessar o banco de dados.", 503)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        """Erros HTTP do Flask/Werkzeug (404 de rota, 405 de metodo etc.)."""
        return error_response(error.description, error.code)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Rede de seguranca: qualquer excecao nao prevista -> HTTP 500."""
        logger.exception("Erro inesperado")
        return error_response("Erro interno do servidor.", 500)
