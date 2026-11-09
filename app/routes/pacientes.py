"""
============================================================================
CRUD de pacientes - Mente Saudavel
============================================================================
Rotas:
    GET    /api/pacientes                -> listagem paginada + filtros
    GET    /api/pacientes/<id>           -> detalhe
    GET    /api/pacientes/<id>/resumo    -> funcao fn_resumo_paciente (banco)
    POST   /api/pacientes                -> stored procedure sp_criar_paciente
    PUT    /api/pacientes/<id>           -> atualizacao parcial
    DELETE /api/pacientes/<id>           -> exclusao (CASCADE nas consultas)

POR QUE O POST USA PROCEDURE?
-----------------------------
As regras de CPF/e-mail unicos e idade minima de 5 anos ficam no banco
(``sp_criar_paciente``). Assim, qualquer cliente (painel, Postman, app) obedece
a mesma regra, e a API nao precisa duplicar logica. A procedure devolve
``p_id_paciente`` e ``p_mensagem``; a rota traduz a mensagem em HTTP 409/422.

POR QUE O PUT E PARCIAL?
------------------------
O painel envia apenas o campo alterado (ex.: ``{"cidade": "Ji-Parana"}``).
Validar somente o que veio evita obrigar o cliente a reenviar o registro todo.
============================================================================
"""

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

# Campos aceitos no cadastro (usados tambem como documentacao viva da API).
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

# Dominios espelhados nas CHECK constraints do PostgreSQL.
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

    Retorno
    -------
    dict
        Somente as chaves presentes no payload, ja normalizadas. Isso permite
        montar o UPDATE dinamicamente com seguranca (as colunas vem de um
        conjunto fechado, nunca do texto cru do usuario).
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
    """Lista pacientes com paginacao e filtros combinaveis.

    Filtros: ``nome`` (ILIKE), ``status`` (ativo/inativo) e ``cidade`` (ILIKE).
    Os filtros sao acumulados em uma lista e viram ``WHERE ... AND ...``,
    sempre com parametros nomeados para evitar SQL injection.
    """
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

    # COUNT separado da listagem: o total considera todos os registros que
    # atendem ao filtro, nao apenas a pagina atual.
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
    """Devolve um paciente pelo id ou 404 se nao existir."""
    paciente = query_one(f"{SELECT_PATIENT} WHERE id_paciente = %s", (paciente_id,))
    if not paciente:
        raise ApiError("Paciente nao encontrado.", 404)
    return jsonify(paciente)


@bp.get("/<int:paciente_id>/resumo")
def resumo_paciente(paciente_id: int):
    """Cards de resumo do paciente, calculados pela funcao do banco.

    ``fn_resumo_paciente`` agrega total de consultas, realizadas, agendadas,
    humor medio e ultima consulta em uma unica query (usa ``FILTER``), o que
    evita varias idas ao banco para montar a tela de detalhes.
    """
    resumo = query_one(
        "SELECT * FROM fn_resumo_paciente(%s)",
        (paciente_id,),
    )
    if not resumo:
        raise ApiError("Paciente nao encontrado.", 404)
    return jsonify(resumo)


@bp.post("")
def criar_paciente():
    """Cadastra um paciente via ``sp_criar_paciente``.

    Fluxo:
      1. valida formato no Flask (falha rapido, HTTP 422);
      2. chama a procedure com casts explicitos;
      3. se ``p_id_paciente`` vier nulo, traduz a mensagem de negocio:
         CPF/e-mail duplicado -> 409; demais regras (idade etc.) -> 422;
      4. em sucesso, busca o registro completo e responde 201.
    """
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
        # Conflito de unicidade -> 409; regra de negocio/validade -> 422.
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
    """Atualiza parcialmente um paciente.

    As colunas do ``SET`` vem do dicionario validado (conjunto fechado), e os
    valores continuam parametrizados. ``atualizado_em`` e preenchido aqui e
    tambem pela trigger ``trg_pacientes_atualizado_em`` (dupla garantia).
    """
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
    """Exclui um paciente.

    A FK ``fk_consultas_paciente`` usa ``ON DELETE CASCADE``: consultas e
    evolucoes do paciente saem junto. O ``rowcount`` diferencia sucesso de
    "id inexistente" sem uma consulta extra.
    """
    affected = execute("DELETE FROM pacientes WHERE id_paciente = %s", (paciente_id,))
    if affected == 0:
        raise ApiError("Paciente nao encontrado.", 404)
    return jsonify({"mensagem": "Paciente removido com sucesso."})
