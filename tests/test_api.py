"""Teste de integracao da API.

Execute com um banco de teste configurado:

    set TEST_DB_NAME=mente_saudavel_test
    set RUN_DB_TESTS=1
    pytest

Sem a variavel RUN_DB_TESTS os testes sao ignorados.
"""

import os
import random

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Defina RUN_DB_TESTS=1 e um banco de teste para executar.",
)


def _cpf_valido() -> str:
    """Gera um CPF valido aleatorio para cada execucao."""
    base = [random.randint(0, 9) for _ in range(9)]
    for position in (9, 10):
        total = sum(base[index] * ((position + 1) - index) for index in range(position))
        digit = (total * 10) % 11
        base.append(0 if digit == 10 else digit)
    return "".join(map(str, base))


def test_fluxo_completo(client):
    assert client.get("/api/health").status_code == 200

    cpf = _cpf_valido()
    payload = {
        "nome": "Paciente de Teste",
        "cpf": cpf,
        "email": f"teste.{cpf}@email.com",
        "telefone": "(69) 99999-0000",
        "data_nascimento": "1998-05-20",
        "genero": "nao_informado",
        "cidade": "Porto Velho",
    }

    created = client.post("/api/pacientes", json=payload)
    assert created.status_code == 201, created.get_json()
    patient_id = created.get_json()["dados"]["id_paciente"]

    assert client.post("/api/pacientes", json=payload).status_code == 409

    listing = client.get("/api/pacientes?nome=Paciente de Teste").get_json()
    assert listing["paginacao"]["total"] >= 1

    updated = client.put(f"/api/pacientes/{patient_id}", json={"cidade": "Ji-Parana"})
    assert updated.status_code == 200
    assert updated.get_json()["dados"]["cidade"] == "Ji-Parana"

    invalid = client.put(f"/api/pacientes/{patient_id}", json={"cpf": "123"})
    assert invalid.status_code == 422

    psychologists = client.get("/api/psicologos").get_json()["dados"]
    assert psychologists, "O banco de teste precisa do seed de psicologos."
    psychologist_id = psychologists[0]["id_psicologo"]

    appointment = client.post(
        "/api/consultas",
        json={
            "id_paciente": patient_id,
            "id_psicologo": psychologist_id,
            "data_hora": "2030-01-10T14:00:00",
            "modalidade": "online",
        },
    )
    assert appointment.status_code == 201, appointment.get_json()
    appointment_id = appointment.get_json()["dados"]["id_consulta"]

    conflict = client.post(
        "/api/consultas",
        json={
            "id_paciente": patient_id,
            "id_psicologo": psychologist_id,
            "data_hora": "2030-01-10T14:00:00",
            "modalidade": "online",
        },
    )
    assert conflict.status_code == 409

    evolution = client.post(
        "/api/evolucoes",
        json={
            "id_consulta": appointment_id,
            "humor": 8,
            "relato": "Paciente apresentou boa evolucao durante a sessao.",
        },
    )
    assert evolution.status_code == 201, evolution.get_json()

    duplicate_evolution = client.post(
        "/api/evolucoes",
        json={
            "id_consulta": appointment_id,
            "humor": 7,
            "relato": "Tentativa de duplicar a evolucao da consulta.",
        },
    )
    assert duplicate_evolution.status_code == 409

    summary = client.get(f"/api/pacientes/{patient_id}/resumo")
    assert summary.status_code == 200
    assert summary.get_json()["total_consultas"] == 1

    report = client.get(
        "/api/relatorios/atendimentos?data_inicio=2030-01-01&data_fim=2030-01-31"
    )
    assert report.status_code == 200
    assert report.get_json()["total_registros"] >= 1

    assert client.delete(f"/api/consultas/{appointment_id}").status_code == 200
    assert client.delete(f"/api/pacientes/{patient_id}").status_code == 200
    assert client.get(f"/api/pacientes/{patient_id}").status_code == 404
