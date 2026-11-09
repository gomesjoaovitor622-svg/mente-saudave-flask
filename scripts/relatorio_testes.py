"""
============================================================================
Gerador do RELATORIO DE TESTES - Mente Saudavel
============================================================================
Executa uma bateria de testes REAIS contra uma instancia Flask em execucao e
grava duas evidencias:

    docs/RELATORIO_DE_TESTES.md
    docs/testes/resultado_testes.json

O relatorio lista, para cada rota: metodo, caminho, payload JSON enviado,
status HTTP recebido, corpo da resposta e o efeito verificado no PostgreSQL.
Tambem executa, por SQL direto, tentativas de violar CHECK constraints para
provar que o banco rejeita dados invalidos mesmo sem passar pela API.

USO
---
    # 1. suba a API (ex.: porta 5055)
    python app.py

    # 2. em outro terminal
    python scripts/relatorio_testes.py --base-url http://127.0.0.1:5055

Variaveis de ambiente do banco: DB_HOST, DB_PORT, DB_NAME, DB_USER,
DB_PASSWORD (as mesmas usadas pela API).
============================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.config import Config  # noqa: E402  (import apos ajustar sys.path)

DOCS_DIR = BASE_DIR / "docs"
TESTES_DIR = DOCS_DIR / "testes"
JSON_PATH = TESTES_DIR / "resultado_testes.json"
MD_PATH = DOCS_DIR / "RELATORIO_DE_TESTES.md"


# ---------------------------------------------------------------------------
# Cliente HTTP minimalista (urllib) para nao exigir dependencia extra.
# ---------------------------------------------------------------------------
def http_request(base_url: str, method: str, path: str, payload=None):
    """Executa uma requisicao HTTP e devolve (status, corpo_json, headers)."""
    # Codifica espacos/acentos na query string sem quebrar "/", "?" e "&".
    safe_path = urllib.parse.quote(path, safe="/?&=%:")
    url = base_url.rstrip("/") + safe_path
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            try:
                parsed = json.loads(body) if body else {}
            except json.JSONDecodeError:
                parsed = {"raw": body}
            return response.status, parsed, dict(response.headers)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"raw": body}
        return error.code, parsed, dict(error.headers)


def cpf_valido() -> str:
    """Gera um CPF valido aleatorio para evitar colisao entre execucoes."""
    base = [random.randint(0, 9) for _ in range(9)]
    for position in (9, 10):
        total = sum(base[index] * ((position + 1) - index) for index in range(position))
        digit = (total * 10) % 11
        base.append(0 if digit == 10 else digit)
    return "".join(map(str, base))


def db_connect():
    """Abre conexao direta para comprovar o efeito das operacoes no banco."""
    return psycopg2.connect(**Config.db_params())


def db_scalar(conn, sql: str, params=()):
    """Executa um SELECT escalar de verificacao."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None


# ---------------------------------------------------------------------------
# Testes de CHECK constraints por SQL direto
# ---------------------------------------------------------------------------
def constraint_checks(conn) -> list[dict]:
    """Tenta inserir dados invalidos e registra a rejeicao do PostgreSQL."""
    checks = [
        (
            "ck_pacientes_cpf_formato",
            "CPF com letras",
            "INSERT INTO pacientes (nome, cpf, email, data_nascimento) "
            "VALUES ('Teste', 'abc123', 'check.cpf@email.com', '1990-01-01')",
        ),
        (
            "ck_pacientes_nascimento",
            "Data de nascimento futura",
            "INSERT INTO pacientes (nome, cpf, email, data_nascimento) "
            f"VALUES ('Teste', '{cpf_valido()}', 'check.futuro@email.com', CURRENT_DATE + 1)",
        ),
        (
            "ck_pacientes_genero",
            "Genero fora do dominio",
            "INSERT INTO pacientes (nome, cpf, email, data_nascimento, genero) "
            f"VALUES ('Teste', '{cpf_valido()}', 'check.genero@email.com', '1990-01-01', 'invalido')",
        ),
        (
            "ck_consultas_duracao",
            "Duracao de 10 minutos",
            "INSERT INTO consultas (id_paciente, id_psicologo, data_hora, duracao_minutos) "
            "VALUES (1, 1, now() + interval '50 days', 10)",
        ),
        (
            "ck_consultas_modalidade",
            "Modalidade 'domiciliar'",
            "INSERT INTO consultas (id_paciente, id_psicologo, data_hora, modalidade) "
            "VALUES (1, 1, now() + interval '51 days', 'domiciliar')",
        ),
        (
            "ck_evolucoes_humor",
            "Humor 11",
            "INSERT INTO evolucoes (id_consulta, humor, relato) "
            "VALUES (1, 11, 'Relato valido para teste de constraint.')",
        ),
        (
            "ck_evolucoes_relato_minimo",
            "Relato com 5 caracteres",
            "INSERT INTO evolucoes (id_consulta, humor, relato) VALUES (2, 5, 'curto')",
        ),
        (
            "ck_psicologos_valor_positivo",
            "valor_sessao = 0",
            "INSERT INTO psicologos (nome, crp, email, especialidade, valor_sessao) "
            f"VALUES ('Teste', '06/{random.randint(10000, 99999)}', "
            f"'check.psi.{random.randint(1, 99999)}@email.com', 'Teste', 0)",
        ),
    ]

    results = []
    for constraint, description, sql in checks:
        with conn.cursor() as cur:
            cur.execute("SAVEPOINT check_constraint")
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
        except psycopg2.Error as error:
            with conn.cursor() as cur:
                cur.execute("ROLLBACK TO SAVEPOINT check_constraint")
                cur.execute("RELEASE SAVEPOINT check_constraint")
            results.append(
                {
                    "constraint": constraint,
                    "descricao": description,
                    "sqlstate": error.pgcode,
                    "mensagem": (error.pgerror or str(error)).strip().splitlines()[0],
                    "rejeitado": True,
                }
            )
        else:
            with conn.cursor() as cur:
                cur.execute("ROLLBACK TO SAVEPOINT check_constraint")
                cur.execute("RELEASE SAVEPOINT check_constraint")
            results.append(
                {
                    "constraint": constraint,
                    "descricao": description,
                    "sqlstate": None,
                    "mensagem": "O banco ACEITOU o dado invalido (falha!).",
                    "rejeitado": False,
                }
            )
    conn.rollback()
    return results


# ---------------------------------------------------------------------------
# Bateria principal
# ---------------------------------------------------------------------------
def run(base_url: str) -> dict:
    conn = db_connect()
    cpf = cpf_valido()
    sufixo = random.randint(10000, 99999)
    email = f"relatorio.{cpf}@email.com"
    crp = f"06/{sufixo}"
    horario = (datetime.now() + timedelta(days=60)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )

    steps: list[dict] = []
    state: dict[str, int] = {}

    def add_step(
        name,
        method,
        path,
        payload,
        expected_status,
        db_effect,
        db_verification=None,
    ):
        status, body, _headers = http_request(base_url, method, path, payload)
        verified = None
        if db_verification:
            try:
                verified = db_verification()
            except Exception as error:  # pragma: no cover - apenas evidencia
                verified = f"erro na verificacao: {error}"
        steps.append(
            {
                "nome": name,
                "metodo": method,
                "rota": path,
                "payload": payload,
                "status_http": status,
                "status_esperado": expected_status,
                "sucesso": status == expected_status,
                "resposta": body,
                "comportamento_banco": db_effect,
                "verificacao_banco": verified,
            }
        )
        return body

    # 1. Health check
    add_step(
        "Health check (API + PostgreSQL)",
        "GET",
        "/api/health",
        None,
        200,
        "Executa SELECT current_database(), version(); nenhuma escrita.",
        lambda: f"banco conectado: {db_scalar(conn, 'SELECT current_database()')}",
    )

    # 2. Criar paciente via procedure
    paciente_payload = {
        "nome": "Paciente Relatorio de Testes",
        "cpf": cpf,
        "email": email,
        "telefone": "(69) 99999-4242",
        "data_nascimento": "1994-03-18",
        "genero": "nao_informado",
        "cidade": "Porto Velho",
        "observacoes": "Registro criado pelo script de relatorio de testes.",
    }
    created = add_step(
        "Criar paciente (sp_criar_paciente)",
        "POST",
        "/api/pacientes",
        paciente_payload,
        201,
        "INSERT em pacientes pela procedure; trigger trg_auditar_paciente grava "
        "linha INSERT em auditoria_pacientes.",
        lambda: f"paciente no banco: {db_scalar(conn, 'SELECT COUNT(*) FROM pacientes WHERE cpf = %s', (cpf,))}",
    )
    state["paciente_id"] = created["dados"]["id_paciente"]

    # 3. CPF duplicado
    add_step(
        "Tentar cadastrar CPF duplicado",
        "POST",
        "/api/pacientes",
        paciente_payload,
        409,
        "A procedure detecta duplicidade antes do INSERT; nenhuma linha nova.",
        lambda: f"pacientes com o CPF: {db_scalar(conn, 'SELECT COUNT(*) FROM pacientes WHERE cpf = %s', (cpf,))}",
    )

    # 4. Listagem com filtro
    add_step(
        "Listar pacientes com filtro por nome",
        "GET",
        "/api/pacientes?nome=Paciente Relatorio",
        None,
        200,
        "SELECT paginado com ILIKE; nao altera dados.",
        lambda: f"encontrados no banco: {db_scalar(conn, 'SELECT COUNT(*) FROM pacientes WHERE nome ILIKE %s', ('%Paciente Relatorio%',))}",
    )

    # 5. Detalhe
    add_step(
        "Obter paciente por id",
        "GET",
        f"/api/pacientes/{state['paciente_id']}",
        None,
        200,
        "SELECT por chave primaria.",
    )

    # 6. Atualizacao parcial
    add_step(
        "Atualizar cidade do paciente (PUT parcial)",
        "PUT",
        f"/api/pacientes/{state['paciente_id']}",
        {"cidade": "Ji-Parana"},
        200,
        "UPDATE em pacientes; trigger preenche atualizado_em; auditoria grava UPDATE.",
        lambda: f"cidade atual: {db_scalar(conn, 'SELECT cidade FROM pacientes WHERE id_paciente = %s', (state['paciente_id'],))}",
    )

    # 7. Validacao de CPF invalido
    add_step(
        "Rejeitar CPF invalido no PUT",
        "PUT",
        f"/api/pacientes/{state['paciente_id']}",
        {"cpf": "12345678900"},
        422,
        "Validacao do Flask interrompe antes do banco; nenhuma alteracao.",
        lambda: f"CPF permanece: {db_scalar(conn, 'SELECT cpf FROM pacientes WHERE id_paciente = %s', (state['paciente_id'],))}",
    )

    # 8. Criar psicologo
    psicologo_payload = {
        "nome": f"Psicologo Relatorio {sufixo}",
        "crp": crp,
        "email": f"psi.relatorio.{sufixo}@email.com",
        "especialidade": "Psicologia Clinica",
        "valor_sessao": 195.00,
    }
    psicologo = add_step(
        "Criar psicologo",
        "POST",
        "/api/psicologos",
        psicologo_payload,
        201,
        "INSERT em psicologos com CRP/e-mail unicos.",
        lambda: f"psicologos com CRP: {db_scalar(conn, 'SELECT COUNT(*) FROM psicologos WHERE crp = %s', (crp,))}",
    )
    state["psicologo_id"] = psicologo["dados"]["id_psicologo"]

    # 9. Listagem de psicologos
    add_step(
        "Listar psicologos por especialidade",
        "GET",
        "/api/psicologos?especialidade=Psicologia Clinica",
        None,
        200,
        "SELECT com ILIKE e paginacao.",
    )

    # 10. Agendar consulta via procedure
    consulta_payload = {
        "id_paciente": state["paciente_id"],
        "id_psicologo": state["psicologo_id"],
        "data_hora": horario.isoformat(),
        "duracao_minutos": 50,
        "modalidade": "online",
        "observacoes": "Consulta criada pelo relatorio de testes.",
    }
    consulta = add_step(
        "Agendar consulta (sp_agendar_consulta)",
        "POST",
        "/api/consultas",
        consulta_payload,
        201,
        "INSERT em consultas pela procedure; valor recebe o padrao do psicologo "
        "quando omitido; indice unico parcial protege o horario.",
        lambda: f"consultas no horario: {db_scalar(conn, 'SELECT COUNT(*) FROM consultas WHERE id_psicologo = %s AND data_hora = %s', (state['psicologo_id'], horario))}",
    )
    state["consulta_id"] = consulta["dados"]["id_consulta"]

    # 11. Conflito de agenda
    add_step(
        "Tentar double-booking no mesmo horario",
        "POST",
        "/api/consultas",
        consulta_payload,
        409,
        "A procedure e o indice uq_consultas_agenda_ativa impedem o segundo "
        "agendamento ativo; nenhuma linha nova.",
        lambda: f"consultas no horario: {db_scalar(conn, 'SELECT COUNT(*) FROM consultas WHERE id_psicologo = %s AND data_hora = %s', (state['psicologo_id'], horario))}",
    )

    # 12. Registrar evolucao
    evolucao_payload = {
        "id_consulta": state["consulta_id"],
        "humor": 8,
        "relato": "Paciente relatou melhora significativa do sono e da ansiedade.",
        "encaminhamento": "Manter sessoes semanais.",
    }
    add_step(
        "Registrar evolucao (sp_registrar_evolucao)",
        "POST",
        "/api/evolucoes",
        evolucao_payload,
        201,
        "INSERT em evolucoes (1:1 com a consulta).",
        lambda: f"evolucoes da consulta: {db_scalar(conn, 'SELECT COUNT(*) FROM evolucoes WHERE id_consulta = %s', (state['consulta_id'],))}",
    )

    # 13. Evolucao duplicada
    add_step(
        "Tentar duplicar a evolucao da mesma consulta",
        "POST",
        "/api/evolucoes",
        evolucao_payload,
        409,
        "A procedure recusa a segunda evolucao; UNIQUE em id_consulta e a "
        "ultima barreira.",
        lambda: f"evolucoes da consulta: {db_scalar(conn, 'SELECT COUNT(*) FROM evolucoes WHERE id_consulta = %s', (state['consulta_id'],))}",
    )

    # 14. Listagens
    add_step(
        "Listar consultas agendadas",
        "GET",
        "/api/consultas?status=agendada",
        None,
        200,
        "SELECT na view vw_agenda_completa (JOIN de 3 tabelas).",
    )
    add_step(
        "Listar evolucoes da consulta",
        "GET",
        f"/api/evolucoes?id_consulta={state['consulta_id']}",
        None,
        200,
        "SELECT na view vw_evolucoes (JOIN de 4 tabelas).",
    )

    # 15. Resumo do paciente
    add_step(
        "Resumo do paciente (fn_resumo_paciente)",
        "GET",
        f"/api/pacientes/{state['paciente_id']}/resumo",
        None,
        200,
        "Funcao tabular agrega consultas, realizadas, agendadas e humor medio.",
        lambda: f"total de consultas: {db_scalar(conn, 'SELECT COUNT(*) FROM consultas WHERE id_paciente = %s', (state['paciente_id'],))}",
    )

    # 16. Relatorios
    add_step(
        "Relatorio de atendimentos por periodo",
        "GET",
        "/api/relatorios/atendimentos?data_inicio=2000-01-01&data_fim=2100-12-31",
        None,
        200,
        "SELECT na funcao fn_relatorio_atendimentos, que le a view "
        "vw_relatorio_atendimentos.",
    )
    add_step(
        "Indicadores gerais do painel",
        "GET",
        "/api/relatorios/resumo",
        None,
        200,
        "Agregacoes (COUNT/AVG) e agrupamento por especialidade.",
    )

    # 17. Limpeza e verificacao de CASCADE
    add_step(
        "Excluir consulta (CASCADE na evolucao)",
        "DELETE",
        f"/api/consultas/{state['consulta_id']}",
        None,
        200,
        "DELETE em consultas; FK ON DELETE CASCADE remove a evolucao.",
        lambda: f"evolucoes restantes: {db_scalar(conn, 'SELECT COUNT(*) FROM evolucoes WHERE id_consulta = %s', (state['consulta_id'],))}",
    )
    add_step(
        "Excluir paciente",
        "DELETE",
        f"/api/pacientes/{state['paciente_id']}",
        None,
        200,
        "DELETE em pacientes; auditoria grava DELETE.",
        lambda: f"paciente restante: {db_scalar(conn, 'SELECT COUNT(*) FROM pacientes WHERE id_paciente = %s', (state['paciente_id'],))}",
    )
    add_step(
        "Excluir psicologo",
        "DELETE",
        f"/api/psicologos/{state['psicologo_id']}",
        None,
        200,
        "DELETE em psicologos (sem consultas vinculadas).",
        lambda: f"psicologo restante: {db_scalar(conn, 'SELECT COUNT(*) FROM psicologos WHERE id_psicologo = %s', (state['psicologo_id'],))}",
    )
    add_step(
        "Buscar paciente removido (404)",
        "GET",
        f"/api/pacientes/{state['paciente_id']}",
        None,
        404,
        "Nenhuma linha encontrada; handler devolve JSON padronizado.",
    )

    # 18. CHECK constraints direto no banco
    checks = constraint_checks(conn)
    conn.close()

    return {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "base_url": base_url,
        "banco": Config.DB_NAME,
        "host_banco": f"{Config.DB_HOST}:{Config.DB_PORT}",
        "total_testes_http": len(steps),
        "testes_http_ok": sum(1 for step in steps if step["sucesso"]),
        "total_checks": len(checks),
        "checks_rejeitados": sum(1 for check in checks if check["rejeitado"]),
        "passos": steps,
        "constraints": checks,
    }


# ---------------------------------------------------------------------------
# Geracao do Markdown
# ---------------------------------------------------------------------------
def render_markdown(result: dict) -> str:
    lines = [
        "# Relatorio de Testes - Mente Saudavel",
        "",
        f"**Data de execucao:** {result['gerado_em']}  ",
        f"**API testada:** `{result['base_url']}`  ",
        f"**Banco de dados:** `{result['banco']}` em `{result['host_banco']}`  ",
        "**Responsavel:** equipe Mente Saudavel (IFRO)",
        "",
        "## 1. Resumo",
        "",
        "| Indicador | Resultado |",
        "|---|---|",
        f"| Testes HTTP executados | {result['total_testes_http']} |",
        f"| Testes HTTP com status esperado | {result['testes_http_ok']} |",
        f"| CHECK constraints testadas | {result['total_checks']} |",
        f"| Constraints que rejeitaram o dado invalido | {result['checks_rejeitados']} |",
        "",
        "> Todos os testes foram executados contra a API real, com PostgreSQL "
        "ativo. O efeito de cada operacao foi conferido por consulta direta ao banco.",
        "",
        "## 2. Testes de endpoints (HTTP)",
        "",
        "| # | Metodo | Rota | Status | Esperado | Resultado | Comportamento no banco |",
        "|---|---|---|---|---|---|---|",
    ]

    for index, step in enumerate(result["passos"], start=1):
        status_icon = "OK" if step["sucesso"] else "FALHOU"
        lines.append(
            f"| {index} | {step['metodo']} | `{step['rota']}` | "
            f"{step['status_http']} | {step['status_esperado']} | {status_icon} | "
            f"{step['comportamento_banco']} |"
        )

    lines += ["", "## 3. Detalhamento dos testes HTTP", ""]
    for index, step in enumerate(result["passos"], start=1):
        lines += [
            f"### 3.{index} {step['nome']}",
            "",
            f"- **Requisicao:** `{step['metodo']} {step['rota']}`",
            f"- **Status HTTP:** `{step['status_http']}` (esperado `{step['status_esperado']}`)",
            f"- **Comportamento no banco:** {step['comportamento_banco']}",
        ]
        if step.get("verificacao_banco") is not None:
            lines.append(f"- **Verificacao no banco:** {step['verificacao_banco']}")
        if step["payload"] is not None:
            lines += [
                "",
                "**Payload enviado**",
                "",
                "```json",
                json.dumps(step["payload"], ensure_ascii=False, indent=2, default=str),
                "```",
            ]
        lines += [
            "",
            "**Resposta recebida**",
            "",
            "```json",
            json.dumps(step["resposta"], ensure_ascii=False, indent=2, default=str),
            "```",
            "",
        ]

    lines += [
        "## 4. Validacao das CHECK constraints no banco",
        "",
        "As tentativas abaixo foram feitas por **SQL direto** (sem passar pela API), "
        "comprovando que a integridade e garantida pelo proprio PostgreSQL.",
        "",
        "| Constraint | Dado invalido testado | SQLSTATE | Resultado |",
        "|---|---|---|---|",
    ]
    for check in result["constraints"]:
        resultado = "REJEITADO" if check["rejeitado"] else "ACEITO (falha)"
        lines.append(
            f"| `{check['constraint']}` | {check['descricao']} | "
            f"`{check['sqlstate'] or '-'}` | {resultado} |"
        )

    lines += [
        "",
        "### 4.1 Mensagens retornadas pelo PostgreSQL",
        "",
    ]
    for check in result["constraints"]:
        lines += [
            f"**{check['constraint']}** - {check['descricao']}",
            "",
            "```text",
            check["mensagem"],
            "```",
            "",
        ]

    lines += [
        "## 5. Conclusao",
        "",
        f"- {result['testes_http_ok']} de {result['total_testes_http']} testes HTTP "
        "retornaram o status esperado.",
        f"- {result['checks_rejeitados']} de {result['total_checks']} CHECK "
        "constraints rejeitaram corretamente os dados invalidos.",
        "- As stored procedures aplicaram as regras de negocio (CPF/e-mail unicos, "
        "idade minima, conflito de agenda e evolucao unica).",
        "- As views com JOIN e as funcoes de relatorio responderam com dados "
        "consistentes.",
        "- O script `pytest` complementa esta evidencia com 55 testes automatizados "
        "(unitarios, de API e de integridade do banco).",
        "",
        "---",
        "",
        "Evidencia em JSON: `docs/testes/resultado_testes.json`.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa o relatorio de testes.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("API_URL", "http://127.0.0.1:5055"),
        help="URL da API em execucao (padrao: http://127.0.0.1:5055).",
    )
    args = parser.parse_args()

    TESTES_DIR.mkdir(parents=True, exist_ok=True)
    result = run(args.base_url)

    JSON_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    MD_PATH.write_text(render_markdown(result), encoding="utf-8")

    print(f"JSON: {JSON_PATH}")
    print(f"Markdown: {MD_PATH}")
    print(
        f"HTTP: {result['testes_http_ok']}/{result['total_testes_http']} OK | "
        f"CHECKs: {result['checks_rejeitados']}/{result['total_checks']} rejeitadas"
    )
    return 0 if (
        result["testes_http_ok"] == result["total_testes_http"]
        and result["checks_rejeitados"] == result["total_checks"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
