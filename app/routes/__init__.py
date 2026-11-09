"""
============================================================================
Registro dos blueprints (modulos de rotas) - Mente Saudavel
============================================================================
Cada blueprint agrupa as rotas de um dominio e recebe um ``url_prefix``
proprio. Registrar todos em um unico lugar torna simples adicionar um novo
modulo (basta importar e incluir na tupla) e testar a API por partes.

ORDEM DE REGISTRO
-----------------
Nao ha conflito entre os prefixos, mas manter a ordem abaixo deixa o mapa da
API legivel ao executar ``flask routes``:

    /api/health
    /api/pacientes
    /api/psicologos
    /api/consultas
    /api/evolucoes
    /api/relatorios
============================================================================
"""

from .consultas import bp as consultas_bp
from .evolucoes import bp as evolucoes_bp
from .health import bp as health_bp
from .pacientes import bp as pacientes_bp
from .psicologos import bp as psicologos_bp
from .relatorios import bp as relatorios_bp


def register_blueprints(app):
    """Registra todos os blueprints na instancia Flask recebida."""
    for blueprint in (
        health_bp,
        pacientes_bp,
        psicologos_bp,
        consultas_bp,
        evolucoes_bp,
        relatorios_bp,
    ):
        app.register_blueprint(blueprint)
