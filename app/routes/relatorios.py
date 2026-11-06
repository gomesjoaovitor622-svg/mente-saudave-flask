"""Relatorios e indicadores do sistema."""

from datetime import date

from flask import Blueprint, jsonify, request

from ..db import query_all, query_one
from ..errors import ApiError
from ..validators import iso_date

bp = Blueprint("relatorios", __name__, url_prefix="/api/relatorios")


@bp.get("/atendimentos")
def relatorio_atendimentos():
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
