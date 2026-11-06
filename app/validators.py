"""Validacoes de entrada reutilizadas pelos endpoints."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import current_app, request

from .errors import ApiError

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
# Formato de exemplo: 06/123456 ou 06/12345
CRP_RE = re.compile(r"^\d{2}/\d{4,6}$")
PHONE_RE = re.compile(r"^[0-9()+\-\s]{8,20}$")


def get_json_body() -> dict:
    """Le o corpo JSON da requisicao e garante que seja um objeto."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Corpo da requisicao deve ser um JSON valido (objeto).", 400)
    return data


def require_fields(data: dict, fields: list[str]) -> None:
    missing = [field for field in fields if data.get(field) in (None, "")]
    if missing:
        raise ApiError(
            "Campos obrigatorios ausentes ou vazios.",
            422,
            details={"campos": missing},
        )


def text(value, field: str, min_len: int = 1, max_len: int | None = None) -> str:
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
    """Normaliza e valida um CPF pelos digitos verificadores."""
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 11 or len(set(digits)) == 1:
        raise ApiError("CPF invalido: informe os 11 digitos.", 422)

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
    value = text(value, "email", max_len=160).lower()
    if not EMAIL_RE.match(value):
        raise ApiError("E-mail invalido.", 422)
    return value


def phone(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    value = text(value, "telefone", min_len=8, max_len=20)
    if not PHONE_RE.match(value):
        raise ApiError("Telefone invalido.", 422)
    return value


def iso_date(value, field: str = "data", allow_future: bool = False) -> date:
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
    """Le ``page`` e ``per_page`` da query string com limites seguros."""
    default_size = current_app.config["DEFAULT_PAGE_SIZE"]
    max_size = current_app.config["MAX_PAGE_SIZE"]

    page = integer(args.get("page", 1), "page", minimum=1)
    per_page = integer(args.get("per_page", default_size), "per_page", minimum=1)
    return page, min(per_page, max_size)


def pagination_meta(page: int, per_page: int, total: int) -> dict:
    pages = (total + per_page - 1) // per_page if per_page else 0
    return {
        "pagina": page,
        "por_pagina": per_page,
        "total": total,
        "total_paginas": pages,
    }
