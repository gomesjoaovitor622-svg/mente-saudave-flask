"""Registro dos blueprints (modulos de rotas) da API."""

from .consultas import bp as consultas_bp
from .evolucoes import bp as evolucoes_bp
from .health import bp as health_bp
from .pacientes import bp as pacientes_bp
from .psicologos import bp as psicologos_bp
from .relatorios import bp as relatorios_bp


def register_blueprints(app):
    for blueprint in (
        health_bp,
        pacientes_bp,
        psicologos_bp,
        consultas_bp,
        evolucoes_bp,
        relatorios_bp,
    ):
        app.register_blueprint(blueprint)
