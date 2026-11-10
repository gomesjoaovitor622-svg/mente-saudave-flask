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


# ---------------------------------------------------------------------------
# Testes complementares de contrato, validacao e CRUD
# ---------------------------------------------------------------------------
def test_health_e_cors(client):
    """Health check deve responder 200 e a API deve expor cabecalhos CORS."""
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["banco"]
    assert response.headers["Access-Control-Allow-Origin"] == "*"

    preflight = client.options("/api/pacientes")
    assert preflight.status_code == 204


def test_psicologo_crud_completo(client):
    """CRUD de psicologo: criar, listar, atualizar, desativar e excluir."""
    sufixo = random.randint(10000, 99999)
    payload = {
        "nome": f"Psicologo API {sufixo}",
        "crp": f"06/{sufixo}",
        "email": f"psi.api.{sufixo}@email.com",
        "especialidade": "Psicologia Clinica",
        "valor_sessao": 190.50,
    }
    created = client.post("/api/psicologos", json=payload)
    assert created.status_code == 201, created.get_json()
    psicologo_id = created.get_json()["dados"]["id_psicologo"]

    listing = client.get("/api/psicologos?especialidade=Psicologia Clinica")
    assert listing.status_code == 200
    assert listing.get_json()["paginacao"]["total"] >= 1

    updated = client.put(
        f"/api/psicologos/{psicologo_id}", json={"valor_sessao": 210, "ativo": False}
    )
    assert updated.status_code == 200
    assert updated.get_json()["dados"]["ativo"] is False

    assert client.delete(f"/api/psicologos/{psicologo_id}").status_code == 200
    assert client.get(f"/api/psicologos/{psicologo_id}").status_code == 404


def test_validacoes_de_payload(client):
    """Payloads invalidos devem ser barrados antes do banco (HTTP 422)."""
    cpf = _cpf_valido()

    # Campos obrigatorios ausentes.
    assert client.post("/api/pacientes", json={"nome": "X"}).status_code == 422

    # CPF com digitos verificadores invalidos.
    invalido = client.post(
        "/api/pacientes",
        json={
            "nome": "Paciente Invalido",
            "cpf": "12345678900",
            "email": "invalido@email.com",
            "data_nascimento": "1990-01-01",
        },
    )
    assert invalido.status_code == 422

    # Data de nascimento futura.
    futuro = client.post(
        "/api/pacientes",
        json={
            "nome": "Paciente Futuro",
            "cpf": cpf,
            "email": f"futuro.{cpf}@email.com",
            "data_nascimento": "2999-01-01",
        },
    )
    assert futuro.status_code == 422

    # Humor fora da escala 1..10.
    assert (
        client.post(
            "/api/evolucoes",
            json={"id_consulta": 1, "humor": 11, "relato": "Relato valido aqui."},
        ).status_code
        == 422
    )

    # Duracao fora de 15..180 minutos.
    assert (
        client.post(
            "/api/consultas",
            json={
                "id_paciente": 1,
                "id_psicologo": 1,
                "data_hora": "2031-01-01T10:00:00",
                "duracao_minutos": 5,
            },
        ).status_code
        == 422
    )


def test_regras_de_negocio_do_banco_via_api(client):
    """As procedures devem recusar regras de negocio com HTTP 409/422."""
    # Idade minima de 5 anos (regra da procedure).
    cpf = _cpf_valido()
    bebe = client.post(
        "/api/pacientes",
        json={
            "nome": "Bebe API",
            "cpf": cpf,
            "email": f"bebe.{cpf}@email.com",
            "data_nascimento": "2025-01-01",
        },
    )
    assert bebe.status_code == 422
    assert "5 anos" in bebe.get_json()["mensagem"]

    # Paciente inexistente ao agendar consulta.
    inexistente = client.post(
        "/api/consultas",
        json={
            "id_paciente": 999999,
            "id_psicologo": 1,
            "data_hora": "2031-02-01T10:00:00",
        },
    )
    assert inexistente.status_code == 409


def test_relatorios_e_resumo(client):
    """Relatorios e indicadores devem responder com dados coerentes."""
    atendimentos = client.get(
        "/api/relatorios/atendimentos?data_inicio=2000-01-01&data_fim=2100-12-31"
    )
    assert atendimentos.status_code == 200
    body = atendimentos.get_json()
    assert body["total_registros"] >= 1
    assert body["dados"][0]["paciente"]

    invalido = client.get(
        "/api/relatorios/atendimentos?data_inicio=2030-01-01&data_fim=2020-01-01"
    )
    assert invalido.status_code == 422

    resumo = client.get("/api/relatorios/resumo")
    assert resumo.status_code == 200
    assert "totais" in resumo.get_json()
    assert "consultas_por_especialidade" in resumo.get_json()


def test_recursos_inexistentes(client):
    """IDs inexistentes devem devolver 404 no contrato JSON padrao."""
    for url in (
        "/api/pacientes/999999",
        "/api/psicologos/999999",
        "/api/consultas/999999",
        "/api/evolucoes/999999",
    ):
        response = client.get(url)
        assert response.status_code == 404, url
        assert response.get_json()["erro"] is True


def test_indice_de_endpoints(client):
    """GET /api deve listar os endpoints em JSON e em HTML."""
    resposta = client.get("/api")
    assert resposta.status_code == 200
    corpo = resposta.get_json()
    assert corpo["total_endpoints"] >= 20
    rotas = {item["rota"] for item in corpo["endpoints"]}
    assert {"/api/health", "/api/pacientes", "/api/relatorios/resumo"} <= rotas

    pagina = client.get("/api", headers={"Accept": "text/html"})
    assert pagina.status_code == 200
    assert b"/api/health" in pagina.data
    assert b"Mente Saud" in pagina.data
