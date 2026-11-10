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

from flask import Blueprint, jsonify, render_template, request

from ..db import query_one

bp = Blueprint("health", __name__, url_prefix="/api")

# Catalogo unico dos endpoints. Ele alimenta o indice em JSON e a pagina HTML
# exibida no navegador (GET /api), mantendo a documentacao sempre visivel.
API_INDEX = [
    {"grupo": "Saude", "metodo": "GET", "rota": "/api", "descricao": "Indice de endpoints da API"},
    {"grupo": "Saude", "metodo": "GET", "rota": "/api/health", "descricao": "Status da API e da conexao com o PostgreSQL"},
    {"grupo": "Pacientes", "metodo": "GET", "rota": "/api/pacientes", "descricao": "Lista pacientes com paginacao e filtros"},
    {"grupo": "Pacientes", "metodo": "GET", "rota": "/api/pacientes/{id}", "descricao": "Busca paciente por id"},
    {"grupo": "Pacientes", "metodo": "GET", "rota": "/api/pacientes/{id}/resumo", "descricao": "Resumo de consultas e humor do paciente"},
    {"grupo": "Pacientes", "metodo": "POST", "rota": "/api/pacientes", "descricao": "Cadastra paciente (stored procedure)"},
    {"grupo": "Pacientes", "metodo": "PUT", "rota": "/api/pacientes/{id}", "descricao": "Atualiza paciente"},
    {"grupo": "Pacientes", "metodo": "DELETE", "rota": "/api/pacientes/{id}", "descricao": "Remove paciente"},
    {"grupo": "Psicologos", "metodo": "GET", "rota": "/api/psicologos", "descricao": "Lista psicologos com filtros"},
    {"grupo": "Psicologos", "metodo": "GET", "rota": "/api/psicologos/{id}", "descricao": "Busca psicologo por id"},
    {"grupo": "Psicologos", "metodo": "POST", "rota": "/api/psicologos", "descricao": "Cadastra psicologo"},
    {"grupo": "Psicologos", "metodo": "PUT", "rota": "/api/psicologos/{id}", "descricao": "Atualiza psicologo"},
    {"grupo": "Psicologos", "metodo": "DELETE", "rota": "/api/psicologos/{id}", "descricao": "Remove psicologo"},
    {"grupo": "Consultas", "metodo": "GET", "rota": "/api/consultas", "descricao": "Lista consultas por status, paciente, psicologo ou periodo"},
    {"grupo": "Consultas", "metodo": "GET", "rota": "/api/consultas/{id}", "descricao": "Busca consulta por id"},
    {"grupo": "Consultas", "metodo": "POST", "rota": "/api/consultas", "descricao": "Agenda consulta (stored procedure com deteccao de conflito)"},
    {"grupo": "Consultas", "metodo": "PUT", "rota": "/api/consultas/{id}", "descricao": "Atualiza consulta"},
    {"grupo": "Consultas", "metodo": "DELETE", "rota": "/api/consultas/{id}", "descricao": "Remove consulta"},
    {"grupo": "Evolucoes", "metodo": "GET", "rota": "/api/evolucoes", "descricao": "Lista evolucoes por paciente ou consulta"},
    {"grupo": "Evolucoes", "metodo": "GET", "rota": "/api/evolucoes/{id}", "descricao": "Busca evolucao por id"},
    {"grupo": "Evolucoes", "metodo": "POST", "rota": "/api/evolucoes", "descricao": "Registra evolucao (stored procedure)"},
    {"grupo": "Evolucoes", "metodo": "PUT", "rota": "/api/evolucoes/{id}", "descricao": "Atualiza evolucao"},
    {"grupo": "Evolucoes", "metodo": "DELETE", "rota": "/api/evolucoes/{id}", "descricao": "Remove evolucao"},
    {"grupo": "Relatorios", "metodo": "GET", "rota": "/api/relatorios/atendimentos", "descricao": "Atendimentos por periodo (view + join)"},
    {"grupo": "Relatorios", "metodo": "GET", "rota": "/api/relatorios/resumo", "descricao": "Indicadores gerais da clinica"},
]


@bp.get("")
def api_index():
    """Indice da API: HTML no navegador, JSON em clientes como o Postman."""
    if "text/html" in request.headers.get("Accept", ""):
        grupos: dict[str, list[dict]] = {}
        for item in API_INDEX:
            grupos.setdefault(item["grupo"], []).append(item)
        return render_template(
            "api.html",
            grupos=grupos,
            total=len(API_INDEX),
            base_url=request.host_url.rstrip("/"),
        )
    return jsonify(
        {
            "servico": "Mente Saudavel API",
            "total_endpoints": len(API_INDEX),
            "endpoints": API_INDEX,
        }
    )


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
