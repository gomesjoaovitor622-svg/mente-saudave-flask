"""Testes unitarios das validacoes (nao precisam de banco de dados)."""

from datetime import date, timedelta

import pytest

from app.errors import ApiError
from app.validators import (
    cpf,
    decimal,
    email,
    integer,
    iso_date,
    iso_datetime,
    phone,
    text,
)


@pytest.mark.parametrize(
    "value",
    ["52998224725", "529.982.247-25", "11144477735", "39053344705"],
)
def test_cpf_valido(value):
    assert len(cpf(value)) == 11


@pytest.mark.parametrize(
    "value",
    ["11111111111", "12345678900", "5299822472", "abc", "", None],
)
def test_cpf_invalido(value):
    with pytest.raises(ApiError):
        cpf(value)


def test_email_normaliza_para_minusculo():
    assert email("Paciente@Email.COM") == "paciente@email.com"


@pytest.mark.parametrize("value", ["sem-arroba", "a@b", "a b@c.com"])
def test_email_invalido(value):
    with pytest.raises(ApiError):
        email(value)


def test_telefone_opcional():
    assert phone("") is None
    assert phone("(69) 99999-0000") == "(69) 99999-0000"


def test_data_futura_e_rejeitada():
    amanha = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ApiError):
        iso_date(amanha, "data_nascimento")


def test_data_valida():
    assert iso_date("1995-04-12", "data_nascimento") == date(1995, 4, 12)


def test_datetime_iso():
    valor = iso_datetime("2026-11-20T14:30:00")
    assert valor.hour == 14 and valor.minute == 30


def test_datetime_invalido():
    with pytest.raises(ApiError):
        iso_datetime("20/11/2026 14:30")


def test_integer_respeita_limites():
    assert integer("10", "humor", minimum=1, maximum=10) == 10
    with pytest.raises(ApiError):
        integer("11", "humor", minimum=1, maximum=10)


def test_decimal_aceita_virgula():
    assert float(decimal("180,50", "valor", minimum=0)) == 180.5


def test_texto_com_tamanho_minimo():
    with pytest.raises(ApiError):
        text("ab", "nome", min_len=3)
