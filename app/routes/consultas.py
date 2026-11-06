"""Agenda de consultas - criacao via stored procedure ``sp_agendar_consulta``."""

from flask import Blueprint, jsonify, request

from ..db import call_procedure, execute, query_all, query_one
from ..errors import ApiError
from ..validators import (
    choice,
    decimal,
    get_json_body,
    integer,
    iso_date,
    iso_datetime,
    pagination_meta,
    parse_pagination,
    require_fields,
    text,
)

bp = Blueprint("consultas", __name__, url_prefix="/api/consultas")

STATUS = ["agendada", "realizada", "cancelada", "falta"]
MODALIDADES = ["presencial", "online"]

SELECT_APPOINTMENT = "SELECT * FROM vw_agenda_completa"


def _validate_payload(data: dict, partial: bool = False) -> dict:
    if not partial:
        require_fields(data, ["id_paciente", "id_psicologo", "data_hora"])

    result = {}
    if "id_paciente" in data:
        result["id_paciente"] = integer(data["id_paciente"], "id_paciente", minimum=1)
    if "id_psicologo" in data:
        result["id_psicologo"] = integer(
            data["id_psicologo"], "id_psicologo", minimum=1
        )
    if "data_hora" in data:
        result["data_hora"] = iso_datetime(data["data_hora"])
    if "duracao_minutos" in data:
        result["duracao_minutos"] = integer(
            data["duracao_minutos"], "duracao_minutos", minimum=15, maximum=180
        )
    if "modalidade" in data:
        result["modalidade"] = choice(
            data["modalidade"], "modalidade", MODALIDADES, "presencial"
        )
    if "status" in data:
        result["status"] = choice(data["status"], "status", STATUS, "agendada")
    if "valor" in data:
        result["valor"] = decimal(data["valor"], "valor", minimum=0)
    if "observacoes" in data:
        result["observacoes"] = (
            text(data["observacoes"], "observacoes", max_len=1000)
            if data["observacoes"]
            else None
        )
    return result


@bp.get("")
def listar_consultas():
    page, per_page = parse_pagination(request.args)
    filters, params = [], {}

    if request.args.get("status"):
        filters.append("status = %(status)s")
        params["status"] = choice(request.args["status"], "status", STATUS)
    if request.args.get("id_paciente"):
        filters.append("id_paciente = %(id_paciente)s")
        params["id_paciente"] = integer(
            request.args["id_paciente"], "id_paciente", minimum=1
        )
    if request.args.get("id_psicologo"):
        filters.append("id_psicologo = %(id_psicologo)s")
        params["id_psicologo"] = integer(
            request.args["id_psicologo"], "id_psicologo", minimum=1
        )
    if request.args.get("data_inicio"):
        filters.append("data_hora::date >= %(data_inicio)s")
        params["data_inicio"] = iso_date(request.args["data_inicio"], "data_inicio")
    if request.args.get("data_fim"):
        filters.append("data_hora::date <= %(data_fim)s")
        params["data_fim"] = iso_date(request.args["data_fim"], "data_fim")

    where = f" WHERE {' AND '.join(filters)}" if filters else ""
    total = int(
        query_one(
            f"SELECT COUNT(*) AS total FROM vw_agenda_completa{where}", params
        )["total"]
    )

    params.update({"limit": per_page, "offset": (page - 1) * per_page})
    rows = query_all(
        f"{SELECT_APPOINTMENT}{where} ORDER BY data_hora DESC "
        "LIMIT %(limit)s OFFSET %(offset)s",
        params,
    )
    return jsonify({"dados": rows, "paginacao": pagination_meta(page, per_page, total)})


@bp.get("/<int:consulta_id>")
def obter_consulta(consulta_id: int):
    consulta = query_one(f"{SELECT_APPOINTMENT} WHERE id_consulta = %s", (consulta_id,))
    if not consulta:
        raise ApiError("Consulta nao encontrada.", 404)
    return jsonify(consulta)


@bp.post("")
def criar_consulta():
    values = _validate_payload(get_json_body())

    result = call_procedure(
        "sp_agendar_consulta",
        (
            values["id_paciente"],
            values["id_psicologo"],
            values["data_hora"],
            values.get("duracao_minutos", 50),
            values.get("modalidade", "presencial"),
            values.get("valor"),
            values.get("observacoes"),
        ),
        casts=[
            "integer",
            "integer",
            "timestamptz",
            "smallint",
            "varchar",
            "numeric",
            "text",
        ],
    )

    if not result.get("p_id_consulta"):
        raise ApiError(
            result.get("p_mensagem") or "Nao foi possivel agendar a consulta.", 409
        )

    consulta = query_one(
        f"{SELECT_APPOINTMENT} WHERE id_consulta = %s", (result["p_id_consulta"],)
    )
    return jsonify({"mensagem": result["p_mensagem"], "dados": consulta}), 201


@bp.put("/<int:consulta_id>")
def atualizar_consulta(consulta_id: int):
    values = _validate_payload(get_json_body(), partial=True)
    if not values:
        raise ApiError("Informe ao menos um campo para atualizar.", 400)

    exists = query_one("SELECT 1 FROM consultas WHERE id_consulta = %s", (consulta_id,))
    if not exists:
        raise ApiError("Consulta nao encontrada.", 404)

    assignments = ", ".join(f"{column} = %s" for column in values)
    execute(
        f"UPDATE consultas SET {assignments} WHERE id_consulta = %s",
        tuple(values.values()) + (consulta_id,),
    )
    consulta = query_one(
        f"{SELECT_APPOINTMENT} WHERE id_consulta = %s", (consulta_id,)
    )
    return jsonify({"mensagem": "Consulta atualizada com sucesso.", "dados": consulta})


@bp.delete("/<int:consulta_id>")
def remover_consulta(consulta_id: int):
    affected = execute("DELETE FROM consultas WHERE id_consulta = %s", (consulta_id,))
    if affected == 0:
        raise ApiError("Consulta nao encontrada.", 404)
    return jsonify({"mensagem": "Consulta removida com sucesso."})
