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

O arquivo ``run.py`` existe apenas por compatibilidade e chama este mesmo
ponto de entrada. Toda a logica de criacao da aplicacao esta em
``app/__init__.py`` (padrao Application Factory), o que permite instanciar a
API com configuracoes diferentes (desenvolvimento, testes e producao) sem
alterar o codigo.

POR QUE APPLICATION FACTORY?
-----------------------------
* Evita variaveis globais: cada instancia recebe sua propria configuracao.
* Facilita os testes automatizados (``create_app(TestingConfig)``).
* Permite criar varias instancias no mesmo processo (ex.: testes paralelos).

POR QUE VARIAVEIS DE AMBIENTE?
------------------------------
Credenciais de banco nunca devem ficar no codigo-fonte. ``app/config.py`` le
``DB_HOST``, ``DB_PORT``, ``DB_NAME``, ``DB_USER``, ``DB_PASSWORD`` e
``SECRET_KEY`` do ambiente (ou do arquivo ``.env``), seguindo a boa pratica
de configuracao em doze fatores. Em producao, ``ProductionConfig`` exige que
``SECRET_KEY`` seja definida explicitamente.

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

# ``create_app`` e a fabrica que registra blueprints, tratamento de erros,
# serializacao JSON e CORS. Importar daqui mantem um unico ponto de verdade.
from app import create_app

# Instancia usada pelo servidor WSGI (``flask --app app run``, gunicorn etc.).
# O padrao ``application`` tambem e reconhecido por hospedagens como Render.
app = create_app()
application = app


def _debug_enabled() -> bool:
    """Converte a variavel de ambiente ``FLASK_DEBUG`` em booleano.

    Aceita os valores usuais (1/true/yes/on). O padrao e desligado para evitar
    que o modo debug seja ativado acidentalmente em producao.
    """
    return os.getenv("FLASK_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    # ``host=0.0.0.0`` permite acesso externo (necessario para o tunel de
    # demonstracao e para testar a API a partir de outro dispositivo).
    # ``debug`` fica sob controle do ambiente; nunca fixamos True no codigo.
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=_debug_enabled(),
    )
