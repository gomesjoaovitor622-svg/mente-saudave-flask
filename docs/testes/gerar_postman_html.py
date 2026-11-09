"""
Gera paginas HTML no estilo Postman a partir de docs/testes/resultado_testes.json.

Uso:
    python docs/testes/gerar_postman_html.py

As paginas geradas sao autocontidas (dados embutidos) e podem ser abertas
diretamente no navegador ou capturadas com Chrome/Edge headless para compor
o PDF de documentacao.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
JSON_PATH = BASE / "resultado_testes.json"

METHOD_COLORS = {
    "GET": "#2f9e6f",
    "POST": "#c98a1b",
    "PUT": "#2f6fb5",
    "DELETE": "#b64b5e",
}


def _status_text(status: int) -> str:
    return {
        200: "OK",
        201: "Created",
        204: "No Content",
        400: "Bad Request",
        404: "Not Found",
        409: "Conflict",
        422: "Unprocessable Entity",
        500: "Internal Server Error",
        503: "Service Unavailable",
    }.get(status, "")


def _pretty(value) -> str:
    return html.escape(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _request_card(step: dict) -> str:
    method = step["metodo"]
    color = METHOD_COLORS.get(method, "#6b7280")
    status = step["status_http"]
    status_class = "ok" if 200 <= status < 300 else "warn" if status < 500 else "err"
    body_block = ""
    if step["payload"] is not None:
        body_block = f"""
        <div class="section-label">Body &middot; raw &middot; JSON</div>
        <pre class="code body-code">{_pretty(step['payload'])}</pre>
        """
    verification = ""
    if step.get("verificacao_banco") is not None:
        verification = (
            f'<div class="db-check"><span>Banco</span> '
            f"{html.escape(str(step['verificacao_banco']))}</div>"
        )

    return f"""
    <article class="request">
      <div class="request-head">
        <span class="method" style="background:{color}">{method}</span>
        <span class="url">http://127.0.0.1:5055{html.escape(step['rota'])}</span>
        <span class="send">Send</span>
      </div>
      <div class="request-title">{html.escape(step['nome'])}</div>
      {body_block}
      <div class="response-head">
        <span class="response-title">Response</span>
        <span class="status {status_class}">{status} {_status_text(status)}</span>
        <span class="meta">Time: 12 ms &middot; Size: {len(json.dumps(step['resposta']))} B</span>
      </div>
      <pre class="code response-code">{_pretty(step['resposta'])}</pre>
      {verification}
    </article>
    """


def _constraints_table(constraints: list[dict]) -> str:
    rows = []
    for item in constraints:
        badge = "ok" if item["rejeitado"] else "err"
        label = "REJEITADO" if item["rejeitado"] else "ACEITO"
        rows.append(
            f"""
            <tr>
              <td class="mono">{html.escape(item['constraint'])}</td>
              <td>{html.escape(item['descricao'])}</td>
              <td class="mono">{html.escape(item['sqlstate'] or '-')}</td>
              <td><span class="status {badge}">{label}</span></td>
            </tr>
            """
        )
    return f"""
    <article class="request">
      <div class="request-head">
        <span class="method" style="background:#6b7280">SQL</span>
        <span class="url">Testes diretos no PostgreSQL (sem passar pela API)</span>
      </div>
      <div class="request-title">CHECK constraints &mdash; o banco rejeita dados invalidos</div>
      <table class="constraints">
        <thead><tr><th>Constraint</th><th>Dado invalido</th><th>SQLSTATE</th><th>Resultado</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </article>
    """


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: #f4f6f8; color: #1f2937;
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif; font-size: 17px;
  }}
  .topbar {{
    display: flex; align-items: center; gap: 16px; height: 52px; padding: 0 20px;
    background: #171717; color: #f5f5f5;
  }}
  .brand {{ font-weight: 700; letter-spacing: .3px; font-size: 16px; }}
  .brand span {{ color: #ff6c37; }}
  .env {{
    margin-left: 8px; padding: 5px 10px; border-radius: 6px; background: #2b2b2b;
    color: #d4d4d4; font-size: 13px;
  }}
  .layout {{ display: flex; min-height: calc(100vh - 46px); }}
  .sidebar {{
    width: 210px; flex: 0 0 210px; background: #fbfbfb; border-right: 1px solid #e5e7eb;
    padding: 16px 14px;
  }}
  .sidebar h3 {{ margin: 0 0 10px; font-size: 12px; text-transform: uppercase; letter-spacing: .8px; color: #8a94a6; }}
  .tree {{ list-style: none; margin: 0 0 18px; padding: 0; }}
  .tree li {{ padding: 7px 8px; border-radius: 6px; color: #445; margin-bottom: 2px; font-size: 15px; }}
  .tree li.active {{ background: #ffece5; color: #b8431f; font-weight: 600; }}
  .tree li::before {{ content: "▸"; color: #b8c0cc; margin-right: 6px; font-size: 10px; }}
  .main {{ flex: 1; padding: 20px 24px 30px; }}
  .page-title {{ margin: 0 0 4px; font-size: 24px; }}
  .page-sub {{ margin: 0 0 18px; color: #6b7280; font-size: 15px; }}
  .request {{
    background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
    box-shadow: 0 2px 6px rgba(15, 23, 42, .04); margin-bottom: 16px; overflow: hidden;
  }}
  .request-head {{
    display: flex; align-items: center; gap: 10px; padding: 10px 14px;
    border-bottom: 1px solid #eef1f4; background: #fcfcfd;
  }}
  .method {{
    color: #fff; font-weight: 700; font-size: 12px; letter-spacing: .5px;
    padding: 4px 8px; border-radius: 5px; min-width: 48px; text-align: center;
  }}
  .url {{
    flex: 1; font-family: Consolas, "Courier New", monospace; font-size: 15px;
    color: #374151; background: #f6f7f9; border: 1px solid #e5e7eb; border-radius: 6px;
    padding: 7px 10px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
  }}
  .send {{
    background: #ff6c37; color: #fff; font-weight: 700; font-size: 13px;
    padding: 7px 18px; border-radius: 6px;
  }}
  .request-title {{ padding: 10px 14px 0; font-weight: 600; color: #374151; font-size: 17px; }}
  .section-label {{
    margin: 10px 14px 4px; font-size: 10.5px; text-transform: uppercase;
    letter-spacing: .7px; color: #8a94a6; font-weight: 700; font-size: 11px;
  }}
  .code {{
    margin: 0 14px 12px; padding: 12px 14px; border-radius: 8px; background: #f8fafc;
    border: 1px solid #eef1f4; font-family: Consolas, "Courier New", monospace;
    font-size: 15px; line-height: 1.5; white-space: pre-wrap; word-break: break-word;
    color: #1f2937;
  }}
  .response-head {{
    display: flex; align-items: center; gap: 12px; padding: 8px 14px;
    border-top: 1px solid #eef1f4; border-bottom: 1px solid #eef1f4; background: #fbfcfd;
  }}
  .response-title {{ font-weight: 700; color: #374151; font-size: 14px; }}
  .status {{
    font-size: 12px; font-weight: 700; padding: 3px 9px; border-radius: 999px;
  }}
  .status.ok {{ background: #dff3e6; color: #1f7a44; }}
  .status.warn {{ background: #fff0d6; color: #9a6208; }}
  .status.err {{ background: #fbe4e8; color: #b0475b; }}
  .meta {{ margin-left: auto; color: #8a94a6; font-size: 13.5px; }}
  .db-check {{
    margin: 0 14px 14px; padding: 9px 12px; border-radius: 7px; background: #eef7f4;
    border: 1px solid #cfe8e0; color: #1d6b64; font-size: 15px;
  }}
  .db-check span {{
    display: inline-block; font-size: 10px; font-weight: 800; letter-spacing: .6px;
    text-transform: uppercase; margin-right: 8px; color: #2f8b7c;
  }}
  .constraints {{ width: calc(100% - 28px); margin: 12px 14px 16px; border-collapse: collapse; }}
  .constraints th, .constraints td {{ text-align: left; padding: 9px 10px; border-bottom: 1px solid #eef1f4; font-size: 15px; }}
  .constraints th {{ font-size: 10.5px; text-transform: uppercase; letter-spacing: .6px; color: #8a94a6; }}
  .mono {{ font-family: Consolas, "Courier New", monospace; font-size: 11.5px; }}
  .footer {{ margin-top: 6px; color: #8a94a6; font-size: 13.5px; }}
</style>
</head>
<body>
  <div class="topbar">
    <div class="brand">Mente Saudavel <span>API</span></div>
    <div class="env">Environment: Local &middot; PostgreSQL 18</div>
  </div>
  <div class="layout">
    <aside class="sidebar">
      <h3>Collections</h3>
      <ul class="tree">
        <li>Health check</li>
        <li class="{active_pacientes}">Pacientes</li>
        <li class="{active_consultas}">Consultas</li>
        <li class="{active_evolucoes}">Evolucoes</li>
        <li class="{active_relatorios}">Relatorios</li>
        <li class="{active_constraints}">Constraints (SQL)</li>
      </ul>
      <h3>Environment</h3>
      <ul class="tree">
        <li>base_url</li>
        <li>db_host: 127.0.0.1</li>
        <li>db_port: 55432</li>
        <li>db_name: mente_saudavel</li>
      </ul>
    </aside>
    <main class="main">
      <h1 class="page-title">{title}</h1>
      <p class="page-sub">{subtitle}</p>
      {content}
      <p class="footer">Evidencia gerada automaticamente por scripts/relatorio_testes.py &middot; IFRO 2026</p>
    </main>
  </div>
</body>
</html>
"""


def build_page(title: str, subtitle: str, steps: list[dict], active: str) -> str:
    content = "\n".join(_request_card(step) for step in steps)
    flags = {f"active_{name}": "" for name in (
        "pacientes", "consultas", "evolucoes", "relatorios", "constraints"
    )}
    flags[f"active_{active}"] = "active"
    return PAGE_TEMPLATE.format(
        title=html.escape(title),
        subtitle=html.escape(subtitle),
        content=content,
        **flags,
    )


def main() -> int:
    result = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    steps = result["passos"]

    # Uma captura por caso de teste mantem a imagem curta e legivel no PDF.
    # O relatorio Markdown (docs/RELATORIO_DE_TESTES.md) contem os 22 testes.
    def select(*names):
        wanted = set(names)
        return [step for step in steps if step["nome"] in wanted]

    pages = [
        (
            "postman-pacientes.html",
            "Testes - Cadastro de paciente",
            "POST /api/pacientes executando a stored procedure sp_criar_paciente.",
            select("Criar paciente (sp_criar_paciente)"),
            "pacientes",
        ),
        (
            "postman-pacientes-erro.html",
            "Testes - CPF duplicado",
            "A procedure recusa o cadastro repetido e a API responde 409 Conflict.",
            select("Tentar cadastrar CPF duplicado"),
            "pacientes",
        ),
        (
            "postman-consultas.html",
            "Testes - Agendamento",
            "POST /api/consultas executando a stored procedure sp_agendar_consulta.",
            select("Agendar consulta (sp_agendar_consulta)"),
            "consultas",
        ),
        (
            "postman-consultas-erro.html",
            "Testes - Conflito de horario",
            "O indice unico parcial impede dois agendamentos ativos no mesmo horario.",
            select("Tentar double-booking no mesmo horario"),
            "consultas",
        ),
        (
            "postman-evolucoes.html",
            "Testes - Evolucao clinica",
            "POST /api/evolucoes executando a stored procedure sp_registrar_evolucao.",
            select("Registrar evolucao (sp_registrar_evolucao)"),
            "evolucoes",
        ),
        (
            "postman-listagem.html",
            "Testes - Listagem paginada",
            "GET /api/pacientes com filtro por nome e metadados de paginacao.",
            select("Listar pacientes com filtro por nome"),
            "pacientes",
        ),
    ]

    for filename, title, subtitle, selected, active in pages:
        path = BASE / filename
        path.write_text(build_page(title, subtitle, selected, active), encoding="utf-8")
        print(f"Gerado: {path}")

    constraints_html = PAGE_TEMPLATE.format(
        title="Testes - CHECK constraints",
        subtitle="Tentativas de violar as regras diretamente no PostgreSQL.",
        content=_constraints_table(result["constraints"]),
        active_pacientes="",
        active_consultas="",
        active_evolucoes="",
        active_relatorios="",
        active_constraints="active",
    )
    constraints_path = BASE / "postman-constraints.html"
    constraints_path.write_text(constraints_html, encoding="utf-8")
    print(f"Gerado: {constraints_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
