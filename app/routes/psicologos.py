"""CRUD de psicologos."""

from flask import Blueprint, jsonify, request

from ..db import execute, query_all, query_one
from ..errors import ApiError
from ..validators import (
    decimal,
    email,
    get_json_body,
    pagination_meta,
    parse_pagination,
    require_fields,
    text,
)

bp = Blueprint("psicologos", __name__, url_prefix="/api/psicologos")

SELECT_PSYCHOLOGIST = """
    SELECT id_psicologo, nome, crp, email, especialidade, valor_sessao,
           ativo, criado_em
      FROM psicologos
"""


def _validate_payload(data: dict, partial: bool = False) -> dict:
    if not partial:
        require_fields(data, ["nome", "crp", "email", "especialidade", "valor_sessao"])

    result = {}
    if "nome" in data:
        result["nome"] = text(data["nome"], "nome", min_len=3, max_len=120)
    if "crp" in data:
        result["crp"] = text(data["crp"], "crp", min_len=6, max_len=20)
    if "email" in data:
        result["email"] = email(data["email"])
    if "especialidade" in data:
        result["especialidade"] = text(
            data["especialidade"], "especialidade", max_len=80
        )
    if "valor_sessao" in data:
        result["valor_sessao"] = decimal(
            data["valor_sessao"], "valor_sessao", minimum=0.01
        )
    if "ativo" in data:
        if not isinstance(data["ativo"], bool):
            raise ApiError("O campo 'ativo' deve ser booleano.", 422)
        result["ativo"] = data["ativo"]
    return result


@bp.get("")
def listar_psicologos():
    page, per_page = parse_pagination(request.args)
    filters, params = [], {}

    if request.args.get("especialidade"):
        filters.append("especialidade ILIKE %(especialidade)s")
        params["especialidade"] = f"%{request.args['especialidade'].strip()}%"
    if request.args.get("ativo") is not None:
        filters.append("ativo = %(ativo)s")
        params["ativo"] = request.args["ativo"].lower() in {"1", "true", "sim"}

    where = f" WHERE {' AND '.join(filters)}" if filters else ""
    total = int(
        query_one(f"SELECT COUNT(*) AS total FROM psicologos{where}", params)["total"]
    )

    params.update({"limit": per_page, "offset": (page - 1) * per_page})
    rows = query_all(
        f"{SELECT_PSYCHOLOGIST}{where} ORDER BY nome "
        "LIMIT %(limit)s OFFSET %(offset)s",
        params,
    )
    return jsonify({"dados": rows, "paginacao": pagination_meta(page, per_page, total)})


@bp.get("/<int:psicologo_id>")
def obter_psicologo(psicologo_id: int):
    psicologo = query_one(
        f"{SELECT_PSYCHOLOGIST} WHERE id_psicologo = %s", (psicologo_id,)
    )
    if not psicologo:
        raise ApiError("Psicologo nao encontrado.", 404)
    return jsonify(psicologo)


@bp.post("")
def criar_psicologo():
    values = _validate_payload(get_json_body())
    columns = ", ".join(values.keys())
    placeholders = ", ".join(["%s"] * len(values))

    created = query_one(
        f"INSERT INTO psicologos ({columns}) VALUES ({placeholders}) "
        "RETURNING id_psicologo",
        tuple(values.values()),
    )
    psicologo = query_one(
        f"{SELECT_PSYCHOLOGIST} WHERE id_psicologo = %s",
        (created["id_psicologo"],),
    )
    return jsonify({"mensagem": "Psicologo cadastrado com sucesso.", "dados": psicologo}), 201


@bp.put("/<int:psicologo_id>")
def atualizar_psicologo(psicologo_id: int):
    values = _validate_payload(get_json_body(), partial=True)
    if not values:
        raise ApiError("Informe ao menos um campo para atualizar.", 400)

    exists = query_one(
        "SELECT 1 FROM psicologos WHERE id_psicologo = %s", (psicologo_id,)
    )
    if not exists:
        raise ApiError("Psicologo nao encontrado.", 404)

    assignments = ", ".join(f"{column} = %s" for column in values)
    execute(
        f"UPDATE psicologos SET {assignments} WHERE id_psicologo = %s",
        tuple(values.values()) + (psicologo_id,),
    )
    psicologo = query_one(
        f"{SELECT_PSYCHOLOGIST} WHERE id_psicologo = %s", (psicologo_id,)
    )
    return jsonify({"mensagem": "Psicologo atualizado com sucesso.", "dados": psicologo})


@bp.delete("/<int:psicologo_id>")
def remover_psicologo(psicologo_id: int):
    affected = execute("DELETE FROM psicologos WHERE id_psicologo = %s", (psicologo_id,))
    if affected == 0:
        raise ApiError("Psicologo nao encontrado.", 404)
    return jsonify({"mensagem": "Psicologo removido com sucesso."})
