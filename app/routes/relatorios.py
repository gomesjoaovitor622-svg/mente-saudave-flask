"""
============================================================================
Relatorios e indicadores - Mente Saudavel
============================================================================
Rotas:
    GET /api/relatorios/atendimentos -> funcao fn_relatorio_atendimentos
    GET /api/relatorios/resumo       -> indicadores do painel

POR QUE USAR FUNCAO DO BANCO?
-----------------------------
``fn_relatorio_atendimentos`` le a view ``vw_relatorio_atendimentos`` (JOIN de
consultas + pacientes + psicologos + evolucoes). Manter o relatorio no banco
garante que painel, Postman e qualquer outro cliente vejam os mesmos numeros,
alem de aproveitar indices e evitar trafegar dados desnecessarios.

PERIODO PADRAO
--------------
Se ``data_inicio``/``data_fim`` nao forem informados, o relatorio cobre do
primeiro dia do mes corrente ate hoje - comportamento esperado no painel.
============================================================================
"""

from datetime import date

from flask import Blueprint, jsonify, request

from ..db import query_all, query_one
from ..errors import ApiError
from ..validators import iso_date

bp = Blueprint("relatorios", __name__, url_prefix="/api/relatorios")


@bp.get("/atendimentos")
def relatorio_atendimentos():
    """Relatorio de atendimentos por periodo (inclusive nas duas pontas).

    ``allow_future=True`` porque a agenda pode conter consultas futuras; a
    validacao garante apenas que ``data_fim >= data_inicio``.
    """
    today = date.today()
    data_inicio = iso_date(
        request.args.get("data_inicio", today.replace(day=1).isoformat()),
        "data_inicio",
        allow_future=True,
    )
    data_fim = iso_date(
        request.args.get("data_fim", today.isoformat()), "data_fim", allow_future=True
    )
    if data_fim < data_inicio:
        raise ApiError("'data_fim' deve ser maior ou igual a 'data_inicio'.", 422)

    rows = query_all(
        "SELECT * FROM fn_relatorio_atendimentos(%s, %s)",
        (data_inicio, data_fim),
    )
    return jsonify(
        {
            "periodo": {"data_inicio": data_inicio, "data_fim": data_fim},
            "total_registros": len(rows),
            "dados": rows,
        }
    )


@bp.get("/resumo")
def resumo_geral():
    """Indicadores gerais do painel.

    A primeira query usa subconsultas escalares para trazer todos os totais em
    uma unica ida ao banco. A segunda agrupa consultas por especialidade para
    alimentar o grafico do painel.
    """
    totais = query_one(
        """
        SELECT
            (SELECT COUNT(*) FROM pacientes WHERE status = 'ativo') AS pacientes_ativos,
            (SELECT COUNT(*) FROM psicologos WHERE ativo) AS psicologos_ativos,
            (SELECT COUNT(*) FROM consultas WHERE status = 'agendada') AS consultas_agendadas,
            (SELECT COUNT(*) FROM consultas WHERE status = 'realizada') AS consultas_realizadas,
            (SELECT COALESCE(ROUND(AVG(humor), 1), 0) FROM evolucoes) AS humor_medio
        """
    )

    por_especialidade = query_all(
        """
        SELECT ps.especialidade,
               COUNT(c.id_consulta) AS total_consultas
          FROM psicologos ps
          LEFT JOIN consultas c ON c.id_psicologo = ps.id_psicologo
         GROUP BY ps.especialidade
         ORDER BY total_consultas DESC, ps.especialidade
        """
    )

    return jsonify(
        {
            "totais": totais,
            "consultas_por_especialidade": por_especialidade,
        }
    )
