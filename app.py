"""
============================================================================
MENTE SAUDAVEL - Ponto de entrada canonico da aplicacao Flask
============================================================================
Disciplinas: Desenvolvimento Web III + Banco de Dados II - IFRO 2026
Arquitetura: API REST em Flask + PostgreSQL (psycopg2) + painel web Jinja.

COMO EXECUTAR
-------------
    python app.py                 # usa as variaveis de ambiente / .env
    PORT=8080 python app.py       # troca a porta
    FLASK_DEBUG=1 python app.py   # habilita recarga automatica

Toda a logica de criacao da aplicacao esta em ``app/__init__.py`` (padrao
Application Factory), o que permite instanciar a API sem espalhar codigo de
configuracao pelos modulos.

POR QUE APPLICATION FACTORY?
----------------------------
* Evita variaveis globais: a configuracao fica em um unico ponto.
* Facilita a criacao de instancias em contextos diferentes (execucao normal,
  scripts de manutencao e ferramentas de teste).

POR QUE VARIAVEIS DE AMBIENTE?
------------------------------
Credenciais de banco nunca devem ficar no codigo-fonte. ``app/config.py`` le
``DB_HOST``, ``DB_PORT``, ``DB_NAME``, ``DB_USER`` e ``DB_PASSWORD`` do
ambiente (ou do arquivo ``.env``), seguindo a boa pratica de configuracao
centralizada exigida pela atividade.

ESTRUTURA DE ROTAS (blueprints)
-------------------------------
    /                       -> painel web (Jinja + JavaScript)
    /api/health             -> health check (API + banco)
    /api/pacientes          -> CRUD de pacientes  (POST usa sp_criar_paciente)
    /api/psicologos         -> CRUD de psicologos
    /api/consultas          -> CRUD de consultas  (POST usa sp_agendar_consulta)
    /api/evolucoes          -> CRUD de evolucoes  (POST usa sp_registrar_evolucao)
    /api/relatorios/*       -> relatorios (view + funcao tabular)
============================================================================
"""

from __future__ import annotations

import os

# ``create_app`` e a fabrica que registra blueprints, tratamento de erros e
# serializacao JSON. Importar daqui mantem um unico ponto de verdade.
from app import create_app

# Instancia usada pelo servidor WSGI (``flask --app app run``).
# O alias ``application`` tambem e reconhecido por servidores WSGI.
app = create_app()
application = app


if __name__ == "__main__":
    # ``host=0.0.0.0`` permite acesso pela rede local.
    #
    # ``debug`` vem da configuracao (``Config`` ja leu ``FLASK_DEBUG``):
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=app.config["DEBUG"],
    )
