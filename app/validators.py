"""
============================================================================
Validacoes de entrada reutilizadas pelos endpoints - Mente Saudavel
============================================================================
Toda regra de formato e normalizacao fica aqui, ANTES de chegar ao banco.
Isso permite devolver HTTP 422 com mensagem clara, em vez de deixar o
PostgreSQL recusar o dado com um erro tecnico.

DEFESA EM CAMADAS
-----------------
1. Front-end (HTML/JS): feedback imediato ao usuario.
2. Flask (este modulo): valida formato, tipo, tamanho e dominio.
3. PostgreSQL (CHECK/FK/UNIQUE/procedures): ultima barreira de integridade.

Nenhuma camada e redundante: a API pode ser chamada direto pelo Postman, e o
banco pode ser alterado por outro cliente. As tres juntas garantem a regra.
============================================================================
"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import current_app, request

from .errors import ApiError

# Expressoes regulares espelham as CHECK constraints do script 01_schema.sql.
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
# Formato de exemplo: 06/123456 ou 06/12345 (UF/numero do CRP).
CRP_RE = re.compile(r"^\d{2}/\d{4,6}$")
PHONE_RE = re.compile(r"^[0-9()+\-\s]{8,20}$")


def get_json_body() -> dict:
    """Le o corpo JSON da requisicao e garante que seja um objeto.

    ``silent=True`` evita que o Flask gere HTML de erro quando o JSON e
    invalido; assim conseguimos responder no mesmo contrato JSON da API.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Corpo da requisicao deve ser um JSON valido (objeto).", 400)
    return data


def require_fields(data: dict, fields: list[str]) -> None:
    """Garante que todos os campos obrigatorios vieram preenchidos.

    Devolve em ``detalhes.campos`` exatamente quais campos faltaram, o que
    facilita a correcao pelo cliente da API.
    """
    missing = [field for field in fields if data.get(field) in (None, "")]
    if missing:
        raise ApiError(
            "Campos obrigatorios ausentes ou vazios.",
            422,
            details={"campos": missing},
        )


def text(value, field: str, min_len: int = 1, max_len: int | None = None) -> str:
    """Valida um campo textual, removendo espacos nas pontas.

    ``min_len`` protege contra strings vazias e ``max_len`` evita payloads
    gigantes que estourariam o ``VARCHAR`` do banco.
    """
    if not isinstance(value, str):
        raise ApiError(f"O campo '{field}' deve ser um texto.", 422)
    value = value.strip()
    if len(value) < min_len:
        raise ApiError(
            f"O campo '{field}' deve ter pelo menos {min_len} caracteres.", 422
        )
    if max_len and len(value) > max_len:
        raise ApiError(
            f"O campo '{field}' deve ter no maximo {max_len} caracteres.", 422
        )
    return value


def cpf(value) -> str:
    """Normaliza e valida um CPF pelos digitos verificadores.

    Aceita CPF com ou sem pontuacao e devolve apenas os 11 digitos (formato
    armazenado no banco). Rejeita sequencias repetidas (ex.: 11111111111) e
    digitos verificadores incorretos. A validacao no Flask e mais forte que a
    CHECK do banco, que so confere o tamanho/formato.
    """
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 11 or len(set(digits)) == 1:
        raise ApiError("CPF invalido: informe os 11 digitos.", 422)

    # Algoritmo oficial: calcula os dois digitos verificadores.
    for position in (9, 10):
        total = sum(
            int(digits[index]) * ((position + 1) - index)
            for index in range(position)
        )
        check_digit = (total * 10) % 11
        if check_digit == 10:
            check_digit = 0
        if int(digits[position]) != check_digit:
            raise ApiError("CPF invalido: digitos verificadores nao conferem.", 422)

    return digits


def email(value: str) -> str:
    """Normaliza para minusculo e valida o formato do e-mail.

    Comparar e armazenar em minusculo evita duplicidade do tipo
    ``Ana@x.com`` x ``ana@x.com`` (a procedure tambem compara com ``lower``).
    """
    value = text(value, "email", max_len=160).lower()
    if not EMAIL_RE.match(value):
        raise ApiError("E-mail invalido.", 422)
    return value


def phone(value: str | None) -> str | None:
    """Valida telefone opcional; ``None``/vazio vira ``NULL`` no banco."""
    if value in (None, ""):
        return None
    value = text(value, "telefone", min_len=8, max_len=20)
    if not PHONE_RE.match(value):
        raise ApiError("Telefone invalido.", 422)
    return value


def iso_date(value, field: str = "data", allow_future: bool = False) -> date:
    """Converte ``AAAA-MM-DD`` em ``date`` e opcionalmente bloqueia futuro.

    Usado em ``data_nascimento`` (futuro proibido) e nos filtros de relatorio
    (futuro permitido, pois a agenda pode ter consultas futuras).
    """
    try:
        parsed = date.fromisoformat(str(value))
    except ValueError as exc:
        raise ApiError(
            f"O campo '{field}' deve estar no formato AAAA-MM-DD.", 422
        ) from exc

    if not allow_future and parsed > date.today():
        raise ApiError(f"O campo '{field}' nao pode estar no futuro.", 422)
    return parsed


def iso_datetime(value, field: str = "data_hora") -> datetime:
    """Converte data/hora ISO 8601 em ``datetime``.

    Aceita o sufixo ``Z`` (UTC) usado por JavaScript/Postman, trocando por
    ``+00:00`` antes do ``fromisoformat``. O PostgreSQL recebe o valor com
    fuso e converte para ``TIMESTAMPTZ``.
    """
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApiError(
            f"O campo '{field}' deve estar no formato ISO 8601 "
            "(ex.: 2026-11-20T14:30:00).",
            422,
        ) from exc
    return parsed


def choice(value, field: str, allowed: list[str], default: str | None = None) -> str:
    """Valida um campo de dominio (enum) contra uma lista de valores.

    Se ``value`` vier vazio e houver ``default``, usa o padrao; caso contrario
    responde 422 listando os valores aceitos. Espelha as CHECK ``IN (...)``.
    """
    if value in (None, "") and default is not None:
        return default
    normalized = str(value).strip().lower()
    if normalized not in allowed:
        raise ApiError(
            f"O campo '{field}' deve ser um destes valores: {', '.join(allowed)}.",
            422,
        )
    return normalized


def integer(
    value, field: str, minimum: int | None = None, maximum: int | None = None
) -> int:
    """Converte e valida um inteiro com limites opcionais (inclusive)."""
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(f"O campo '{field}' deve ser um numero inteiro.", 422) from exc
    if minimum is not None and parsed < minimum:
        raise ApiError(f"O campo '{field}' deve ser maior ou igual a {minimum}.", 422)
    if maximum is not None and parsed > maximum:
        raise ApiError(f"O campo '{field}' deve ser menor ou igual a {maximum}.", 422)
    return parsed


def decimal(
    value, field: str, minimum: float | None = None, maximum: float | None = None
) -> Decimal:
    """Converte valor monetario, aceitando virgula ou ponto como decimal.

    Usa ``Decimal`` (e nao ``float``) para evitar erros de arredondamento em
    valores monetarios; o psycopg2 envia o valor como ``NUMERIC``.
    """
    try:
        parsed = Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError) as exc:
        raise ApiError(f"O campo '{field}' deve ser um valor numerico.", 422) from exc
    if minimum is not None and parsed < Decimal(str(minimum)):
        raise ApiError(f"O campo '{field}' deve ser maior ou igual a {minimum}.", 422)
    if maximum is not None and parsed > Decimal(str(maximum)):
        raise ApiError(f"O campo '{field}' deve ser menor ou igual a {maximum}.", 422)
    return parsed


def parse_pagination(args) -> tuple[int, int]:
    """Le ``page`` e ``per_page`` da query string com limites seguros.

    ``per_page`` e limitado por ``MAX_PAGE_SIZE`` para impedir consultas que
    retornariam a tabela inteira e derrubariam o desempenho da API.
    """
    default_size = current_app.config["DEFAULT_PAGE_SIZE"]
    max_size = current_app.config["MAX_PAGE_SIZE"]

    page = integer(args.get("page", 1), "page", minimum=1)
    per_page = integer(args.get("per_page", default_size), "per_page", minimum=1)
    return page, min(per_page, max_size)


def pagination_meta(page: int, per_page: int, total: int) -> dict:
    """Monta o bloco ``paginacao`` presente em todas as listagens.

    Calcula o total de paginas com arredondamento para cima, sem depender de
    ``math.ceil`` (evita import extra).
    """
    pages = (total + per_page - 1) // per_page if per_page else 0
    return {
        "pagina": page,
        "por_pagina": per_page,
        "total": total,
        "total_paginas": pages,
    }
