"""Endpoint de verificacao de saude da API."""

from flask import Blueprint, jsonify

from ..db import query_one

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    database = query_one("SELECT current_database() AS banco, version() AS versao")
    return jsonify(
        {
            "status": "ok",
            "servico": "Mente Saudavel API",
            "banco": database["banco"],
            "versao_postgresql": database["versao"].split(",")[0],
        }
    )
