"""
============================================================================
Health check da API - Mente Saudavel
============================================================================
Rota: GET /api/health

PROPOSITO
---------
Verificar, em uma unica chamada, se a API esta no ar e se consegue falar com
o PostgreSQL. E usada por:
  * painel web (indicador "API online");
  * Postman/monitoramento;
  * plataformas de deploy (Render, Railway, Fly.io) para saber se o servico
    esta saudavel.

POR QUE CONSULTAR O BANCO AQUI
------------------------------
Se a API responde mas o banco esta fora, o sistema nao funciona. A consulta
``SELECT current_database(), version()`` prova que a conexao e a credencial
estao validas. Se falhar, o handler global devolve 503.
============================================================================
"""

from flask import Blueprint, jsonify

from ..db import query_one

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    """Devolve status, nome do banco e versao do PostgreSQL."""
    database = query_one("SELECT current_database() AS banco, version() AS versao")
    return jsonify(
        {
            "status": "ok",
            "servico": "Mente Saudavel API",
            "banco": database["banco"],
            # ``version()`` traz um texto longo; o split(",")[0] deixa apenas
            # "PostgreSQL 18.6 ..." para a resposta ficar enxuta.
            "versao_postgresql": database["versao"].split(",")[0],
        }
    )
