"""
============================================================================
Agenda de consultas - Mente Saudavel
============================================================================
Rotas:
    GET    /api/consultas             -> listagem paginada (view vw_agenda_completa)
    GET    /api/consultas/<id>        -> detalhe
    POST   /api/consultas             -> stored procedure sp_agendar_consulta
    PUT    /api/consultas/<id>        -> atualizacao parcial
    DELETE /api/consultas/<id>        -> exclusao (CASCADE na evolucao)

POR QUE A LISTAGEM USA VIEW?
----------------------------
``vw_agenda_completa`` ja faz o JOIN de consultas + pacientes + psicologos.
A API nao repete JOIN em cada consulta e a tela recebe os nomes prontos.

POR QUE A CRIACAO USA PROCEDURE?
--------------------------------
A procedure valida paciente/psicologo ativos e conflito de horario de forma
atomica no banco. Se duas requisicoes chegarem ao mesmo tempo, o indice unico
parcial ``uq_consultas_agenda_ativa`` impede double-booking.
============================================================================
"""

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

# Dominios espelhados nas CHECK constraints de consultas.
STATUS = ["agendada", "realizada", "cancelada", "falta"]
MODALIDADES = ["presencial", "online"]

# View com JOIN: entrega nomes de paciente/psicologo sem repetir SQL nas rotas.
SELECT_APPOINTMENT = "SELECT * FROM vw_agenda_completa"


def _validate_payload(data: dict, partial: bool = False) -> dict:
    """Valida e normaliza o payload de consulta.

    ``partial=True`` (PUT) valida apenas os campos enviados. Os limites de
    ``duracao_minutos`` (15 a 180) e ``status``/``modalidade`` espelham as
    CHECK constraints do banco.
    """
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
    """Lista consultas com paginacao e filtros.

    Filtros: ``status``, ``id_paciente``, ``id_psicologo``, ``data_inicio`` e
    ``data_fim``. O ``ORDER BY data_hora DESC`` coloca as consultas mais
    recentes/futuras no topo da agenda.
    """
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
    """Devolve uma consulta (com nomes via view) ou 404."""
    consulta = query_one(f"{SELECT_APPOINTMENT} WHERE id_consulta = %s", (consulta_id,))
    if not consulta:
        raise ApiError("Consulta nao encontrada.", 404)
    return jsonify(consulta)


@bp.post("")
def criar_consulta():
    """Agenda uma consulta via ``sp_agendar_consulta``.

    A procedure devolve ``p_id_consulta`` + ``p_mensagem``. Qualquer falha de
    negocio (paciente/psicologo inativo, horario ocupado) vira HTTP 409, pois
    representa conflito com o estado atual do banco.

    ``valor`` omitido: a procedure usa ``COALESCE(p_valor, valor_sessao)`` e
    aplica automaticamente o valor padrao do psicologo.
    """
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
    """Atualiza parcialmente uma consulta (status, horario, valor etc.).

    O indice unico parcial continua valendo no UPDATE: tentar mover uma
    consulta para um horario ja ocupado do mesmo psicologo gera 409.
    """
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
    """Exclui uma consulta; a evolucao vinculada sai por CASCADE."""
    affected = execute("DELETE FROM consultas WHERE id_consulta = %s", (consulta_id,))
    if affected == 0:
        raise ApiError("Consulta nao encontrada.", 404)
    return jsonify({"mensagem": "Consulta removida com sucesso."})
