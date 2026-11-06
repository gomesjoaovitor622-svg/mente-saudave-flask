"""CRUD de pacientes - utiliza a stored procedure ``sp_criar_paciente``."""

from flask import Blueprint, jsonify, request

from ..db import call_procedure, execute, query_all, query_one
from ..errors import ApiError
from ..validators import (
    choice,
    cpf,
    email,
    get_json_body,
    integer,
    iso_date,
    pagination_meta,
    parse_pagination,
    phone,
    require_fields,
    text,
)

bp = Blueprint("pacientes", __name__, url_prefix="/api/pacientes")

PATIENT_FIELDS = [
    "nome",
    "cpf",
    "email",
    "telefone",
    "data_nascimento",
    "genero",
    "cidade",
    "observacoes",
]

GENEROS = ["feminino", "masculino", "nao_binario", "outro", "nao_informado"]
STATUS = ["ativo", "inativo"]

SELECT_PATIENT = """
    SELECT id_paciente, nome, cpf, email, telefone, data_nascimento,
           genero, cidade, observacoes, status, criado_em, atualizado_em
      FROM pacientes
"""


def _validate_patient_payload(data: dict, partial: bool = False) -> dict:
    """Valida e normaliza o payload de paciente.

    Quando ``partial=True`` (PUT), apenas os campos enviados sao validados.
    A lista de campos e o dicionario de saida atendem ao requisito de uso de
    estruturas de dados (listas/dicionarios) na logica da aplicacao.
    """
    if not partial:
        require_fields(data, ["nome", "cpf", "email", "data_nascimento"])

    result = {}
    if "nome" in data:
        result["nome"] = text(data["nome"], "nome", min_len=3, max_len=120)
    if "cpf" in data:
        result["cpf"] = cpf(data["cpf"])
    if "email" in data:
        result["email"] = email(data["email"])
    if "telefone" in data:
        result["telefone"] = phone(data["telefone"])
    if "data_nascimento" in data:
        result["data_nascimento"] = iso_date(data["data_nascimento"], "data_nascimento")
    if "genero" in data:
        result["genero"] = choice(data["genero"], "genero", GENEROS, "nao_informado")
    if "cidade" in data:
        result["cidade"] = (
            text(data["cidade"], "cidade", max_len=80) if data["cidade"] else None
        )
    if "observacoes" in data:
        result["observacoes"] = (
            text(data["observacoes"], "observacoes", max_len=1000)
            if data["observacoes"]
            else None
        )
    if "status" in data:
        result["status"] = choice(data["status"], "status", STATUS, "ativo")

    return result


@bp.get("")
def listar_pacientes():
    page, per_page = parse_pagination(request.args)

    filters = []
    params = {}

    if request.args.get("nome"):
        filters.append("nome ILIKE %(nome)s")
        params["nome"] = f"%{request.args['nome'].strip()}%"
    if request.args.get("status"):
        filters.append("status = %(status)s")
        params["status"] = choice(request.args["status"], "status", STATUS)
    if request.args.get("cidade"):
        filters.append("cidade ILIKE %(cidade)s")
        params["cidade"] = f"%{request.args['cidade'].strip()}%"

    where = f" WHERE {' AND '.join(filters)}" if filters else ""

    total_row = query_one(f"SELECT COUNT(*) AS total FROM pacientes{where}", params)
    total = int(total_row["total"])

    params.update({"limit": per_page, "offset": (page - 1) * per_page})
    rows = query_all(
        f"{SELECT_PATIENT}{where} ORDER BY nome LIMIT %(limit)s OFFSET %(offset)s",
        params,
    )

    return jsonify(
        {
            "dados": rows,
            "paginacao": pagination_meta(page, per_page, total),
        }
    )


@bp.get("/<int:paciente_id>")
def obter_paciente(paciente_id: int):
    paciente = query_one(f"{SELECT_PATIENT} WHERE id_paciente = %s", (paciente_id,))
    if not paciente:
        raise ApiError("Paciente nao encontrado.", 404)
    return jsonify(paciente)


@bp.get("/<int:paciente_id>/resumo")
def resumo_paciente(paciente_id: int):
    resumo = query_one(
        "SELECT * FROM fn_resumo_paciente(%s)",
        (paciente_id,),
    )
    if not resumo:
        raise ApiError("Paciente nao encontrado.", 404)
    return jsonify(resumo)


@bp.post("")
def criar_paciente():
    data = get_json_body()
    values = _validate_patient_payload(data)

    result = call_procedure(
        "sp_criar_paciente",
        (
            values["nome"],
            values["cpf"],
            values["email"],
            values.get("telefone"),
            values["data_nascimento"],
            values.get("genero", "nao_informado"),
            values.get("cidade"),
            values.get("observacoes"),
        ),
        casts=[
            "varchar",
            "varchar",
            "varchar",
            "varchar",
            "date",
            "varchar",
            "varchar",
            "text",
        ],
    )

    if not result.get("p_id_paciente"):
        message = result.get("p_mensagem") or "Nao foi possivel cadastrar o paciente."
        status_code = 409 if ("CPF" in message or "e-mail" in message) else 422
        raise ApiError(message, status_code)

    paciente = query_one(
        f"{SELECT_PATIENT} WHERE id_paciente = %s", (result["p_id_paciente"],)
    )
    return (
        jsonify(
            {
                "mensagem": result["p_mensagem"],
                "dados": paciente,
            }
        ),
        201,
    )


@bp.put("/<int:paciente_id>")
def atualizar_paciente(paciente_id: int):
    data = get_json_body()
    values = _validate_patient_payload(data, partial=True)

    if not values:
        raise ApiError("Informe ao menos um campo para atualizar.", 400)

    exists = query_one("SELECT 1 FROM pacientes WHERE id_paciente = %s", (paciente_id,))
    if not exists:
        raise ApiError("Paciente nao encontrado.", 404)

    columns = list(values.keys())
    assignments = ", ".join(f"{column} = %s" for column in columns)
    params = [values[column] for column in columns] + [paciente_id]

    execute(
        f"UPDATE pacientes SET {assignments}, atualizado_em = now() "
        "WHERE id_paciente = %s",
        params,
    )

    paciente = query_one(f"{SELECT_PATIENT} WHERE id_paciente = %s", (paciente_id,))
    return jsonify({"mensagem": "Paciente atualizado com sucesso.", "dados": paciente})


@bp.delete("/<int:paciente_id>")
def remover_paciente(paciente_id: int):
    affected = execute("DELETE FROM pacientes WHERE id_paciente = %s", (paciente_id,))
    if affected == 0:
        raise ApiError("Paciente nao encontrado.", 404)
    return jsonify({"mensagem": "Paciente removido com sucesso."})
