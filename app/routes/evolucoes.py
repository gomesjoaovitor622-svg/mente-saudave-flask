"""Evolucoes do prontuario - criacao via ``sp_registrar_evolucao``."""

from flask import Blueprint, jsonify, request

from ..db import call_procedure, execute, query_all, query_one
from ..errors import ApiError
from ..validators import (
    get_json_body,
    integer,
    pagination_meta,
    parse_pagination,
    require_fields,
    text,
)

bp = Blueprint("evolucoes", __name__, url_prefix="/api/evolucoes")

SELECT_EVOLUTION = "SELECT * FROM vw_evolucoes"


def _validate_payload(data: dict, partial: bool = False) -> dict:
    if not partial:
        require_fields(data, ["id_consulta", "humor", "relato"])

    result = {}
    if "id_consulta" in data:
        result["id_consulta"] = integer(
            data["id_consulta"], "id_consulta", minimum=1
        )
    if "humor" in data:
        result["humor"] = integer(data["humor"], "humor", minimum=1, maximum=10)
    if "relato" in data:
        result["relato"] = text(data["relato"], "relato", min_len=10, max_len=4000)
    if "encaminhamento" in data:
        result["encaminhamento"] = (
            text(data["encaminhamento"], "encaminhamento", max_len=200)
            if data["encaminhamento"]
            else None
        )
    return result


@bp.get("")
def listar_evolucoes():
    page, per_page = parse_pagination(request.args)
    filters, params = [], {}

    if request.args.get("id_paciente"):
        filters.append("id_paciente = %(id_paciente)s")
        params["id_paciente"] = integer(
            request.args["id_paciente"], "id_paciente", minimum=1
        )
    if request.args.get("id_consulta"):
        filters.append("id_consulta = %(id_consulta)s")
        params["id_consulta"] = integer(
            request.args["id_consulta"], "id_consulta", minimum=1
        )

    where = f" WHERE {' AND '.join(filters)}" if filters else ""
    total = int(
        query_one(f"SELECT COUNT(*) AS total FROM vw_evolucoes{where}", params)["total"]
    )

    params.update({"limit": per_page, "offset": (page - 1) * per_page})
    rows = query_all(
        f"{SELECT_EVOLUTION}{where} ORDER BY criado_em DESC "
        "LIMIT %(limit)s OFFSET %(offset)s",
        params,
    )
    return jsonify({"dados": rows, "paginacao": pagination_meta(page, per_page, total)})


@bp.get("/<int:evolucao_id>")
def obter_evolucao(evolucao_id: int):
    evolucao = query_one(f"{SELECT_EVOLUTION} WHERE id_evolucao = %s", (evolucao_id,))
    if not evolucao:
        raise ApiError("Evolucao nao encontrada.", 404)
    return jsonify(evolucao)


@bp.post("")
def criar_evolucao():
    values = _validate_payload(get_json_body())
    result = call_procedure(
        "sp_registrar_evolucao",
        (
            values["id_consulta"],
            values["humor"],
            values["relato"],
            values.get("encaminhamento"),
        ),
        casts=["integer", "smallint", "text", "varchar"],
    )

    if not result.get("p_id_evolucao"):
        raise ApiError(
            result.get("p_mensagem") or "Nao foi possivel registrar a evolucao.", 409
        )

    evolucao = query_one(
        f"{SELECT_EVOLUTION} WHERE id_evolucao = %s", (result["p_id_evolucao"],)
    )
    return jsonify({"mensagem": result["p_mensagem"], "dados": evolucao}), 201


@bp.put("/<int:evolucao_id>")
def atualizar_evolucao(evolucao_id: int):
    values = _validate_payload(get_json_body(), partial=True)
    if not values:
        raise ApiError("Informe ao menos um campo para atualizar.", 400)

    exists = query_one("SELECT 1 FROM evolucoes WHERE id_evolucao = %s", (evolucao_id,))
    if not exists:
        raise ApiError("Evolucao nao encontrada.", 404)

    assignments = ", ".join(f"{column} = %s" for column in values)
    execute(
        f"UPDATE evolucoes SET {assignments} WHERE id_evolucao = %s",
        tuple(values.values()) + (evolucao_id,),
    )
    evolucao = query_one(f"{SELECT_EVOLUTION} WHERE id_evolucao = %s", (evolucao_id,))
    return jsonify({"mensagem": "Evolucao atualizada com sucesso.", "dados": evolucao})


@bp.delete("/<int:evolucao_id>")
def remover_evolucao(evolucao_id: int):
    affected = execute("DELETE FROM evolucoes WHERE id_evolucao = %s", (evolucao_id,))
    if affected == 0:
        raise ApiError("Evolucao nao encontrada.", 404)
    return jsonify({"mensagem": "Evolucao removida com sucesso."})
