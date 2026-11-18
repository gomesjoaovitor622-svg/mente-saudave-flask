# Relatório de aderência — Atividade 2 (Web III + BD II)

**Projeto:** Mente Saudável — API Flask + PostgreSQL
**Equipe:** Jhennyfér e João Vitor
**Disciplinas:** Desenvolvimento Web III e Banco de Dados II — IFRO
**Data da verificação:** 17/11/2026
**Entrega final:** 30/11/2026 até 23h59 — apresentação em 01/12/2026

---

## 1. Resumo

| Situação | Quantidade |
|----------|-----------|
| Requisitos obrigatórios atendidos | **24 de 25** |
| Requisito obrigatório pendente | **1** (duplo check comprovado no Git) |
| Item desejável (pontos extras) | **1 de 1** atendido (painel web) |

O sistema atende a todas as exigências técnicas da atividade (banco, procedures,
views, endpoints, CRUD, JSON, Flask, configuração e validações). A única
pendência é **processual**: o duplo check existe na prática (o PDF descreve a
revisão cruzada), mas ainda não está registrado no histórico do GitHub como
Pull Requests revisados pelo outro integrante.

---

## 2. Matriz de conformidade

### Parte 1 — Banco de Dados

| # | Requisito | Situação | Evidência | Ação |
|---|-----------|----------|-----------|------|
| 1a | Banco definido seguindo normalização | **Atende** | `database/01_schema.sql`: 5 tabelas separadas por assunto (`psicologos`, `pacientes`, `consultas`, `evolucoes`, `auditoria_pacientes`), sem grupos repetitivos e sem dados redundantes. A evolução referencia apenas a consulta; o valor da sessão fica na consulta. | — |
| 1b | Chaves primárias (PK) e estrangeiras (FK) | **Atende** | 5 PKs e 3 FKs em `01_schema.sql`, todas com `ON DELETE` definido: `consultas → pacientes`, `consultas → psicologos`, `evolucoes → consultas`. | — |
| 1c | Pelo menos 3 CHECK constraints | **Atende** | **18 CHECKs** nomeados em `01_schema.sql` (CPF, e-mail, datas, status, modalidade, duração, humor, relato mínimo, valor etc.). Confirmado no banco: 18 constraints do tipo `c`. | — |
| 1d | Stored procedure usada pela API | **Atende** | 4 procedures em `database/03_procedures.sql`. Três são chamadas pela API via `call_procedure`: `sp_criar_paciente` (`app/routes/pacientes.py:200`), `sp_agendar_consulta` (`app/routes/consultas.py:161`) e `sp_registrar_evolucao` (`app/routes/evolucoes.py:121`). | — |
| 1e | Procedure com VIEW + JOIN para relatório (não precisa ser chamada pela API) | **Atende** | `sp_relatorio_atendimentos` (`03_procedures.sql:290`) lê a view `vw_relatorio_atendimentos`, que faz `JOIN` entre consultas, pacientes, psicólogos e evoluções. Testada no PostgreSQL: retorna as consultas do período. | — |

### Parte 2 — Endpoints da Web API

| # | Requisito | Situação | Evidência | Ação |
|---|-----------|----------|-----------|------|
| 2a | Endpoints que atendam às funcionalidades | **Atende** | 25 endpoints em 6 blueprints (`app/routes/`): pacientes, psicólogos, consultas, evoluções, relatórios e health check. Índice navegável em `GET /api`. | — |
| 2b | Troca de mensagens em JSON | **Atende** | Todas as rotas devolvem JSON (`application/json`), com respostas de sucesso e erro padronizadas (`app/errors.py`). | — |
| 2c | CRUD de qualquer cadastro | **Atende** | CRUD completo de pacientes, psicólogos, consultas e evoluções (POST, GET, PUT, DELETE). | — |
| 2d | Estruturas de dados (dicionário, lista) | **Atende** | `app/validators.py` monta dicionários de erro/campos; `app/db.py` converte linhas em `dict`; as listagens montam listas de dicionários com metadados de paginação. | — |
| 2e | Lógica de interação com o banco | **Atende** | Camada `app/db.py` (conexão psycopg2, consultas parametrizadas, `call_procedure`) usada por todos os blueprints. | — |
| 2f | Pelo menos 1 CRUD e 1 listagem/relatório | **Atende** | CRUD de pacientes + listagem paginada com filtros + `GET /api/relatorios/atendimentos` e `GET /api/relatorios/resumo`. | — |

### Parte 3 — Integração com o Frontend (desejável, pontos extras)

| # | Requisito | Situação | Evidência | Ação |
|---|-----------|----------|-----------|------|
| 3 | Tela que consuma as APIs | **Atende (extra)** | Painel web em `app/templates/index.html` + `app/static/js/app.js`, consumindo a API via `fetch` (dashboard, tabelas, formulários e relatórios). | — |

### Parte 4 — Documentação do sistema (PDF único)

| # | Requisito | Situação | Evidência | Ação |
|---|-----------|----------|-----------|------|
| 4a | Instituição, ano, membros e título | **Atende** | Capa do PDF (`docs/Documentacao_Mente_Saudavel.pdf`, p. 1): IFRO, Curso de Sistemas para Internet, ano 2026, Jhennyfér e João Vitor, título “Mente Saudável”. | — |
| 4b | Responsável principal por cada desenvolvimento/entrega | **Atende** | Seção 9 “Divisão de tarefas”, com a coluna “Revisão” indicando o revisor de cada frente. | — |
| 4c | Objetivo e descrição do sistema | **Atende** | Seções 1 e 2 do PDF (objetivo, visão geral, funcionalidades e tecnologias). | — |
| 4d | Figura simples da arquitetura | **Atende** | Figura 1 — diagrama cliente → API Flask → PostgreSQL, gerado por `docs/gerar_documentacao.py` (`docs/img/arquitetura.png`). | — |
| 4e | Comentário por coluna no script do BD | **Atende** | 42 `COMMENT ON COLUMN` em `01_schema.sql` (todas as colunas das 5 tabelas) + 4 comentários nas views. Confirmado no banco: 46 comentários de coluna. | — |
| 4f | Capturas de tela dos testes no Postman, com título/legenda | **Atende** | Figuras 5 a 11 no PDF, com legendas: cadastro de paciente, CPF duplicado, agendamento, double-booking, evolução, CHECKs e listagem paginada. | — |

### Observações importantes

| # | Requisito | Situação | Evidência | Ação |
|---|-----------|----------|-----------|------|
| O1 | Flask com Python + PostgreSQL/MySQL | **Atende** | Flask 3 + psycopg2 + PostgreSQL 18 (`requirements.txt`, `app/__init__.py`, `app/db.py`). | — |
| O2 | Arquivo de configuração centralizando variáveis de ambiente | **Atende** | `app/config.py` lê todas as variáveis do `.env`; modelo documentado em `.env.example`. | — |
| O3 | Validações no front-end e no back-end | **Atende** | Back-end: `app/validators.py` (CPF, e-mail, datas, enums, paginação) + CHECKs no banco. Front-end: atributos `required`, `minlength`, `maxlength`, `type=email/date/number` e `form.reportValidity()` em `app/static/js/app.js:261,423,530`. | — |
| O4 | Duplo check entre os integrantes | **Pendente de comprovação** | O PDF (seção 9) declara a revisão cruzada, mas o histórico do GitHub não tem Pull Requests com revisor diferente do autor. | Ver seção 4 deste relatório. |

### Entrega

| # | Requisito | Situação | Evidência | Ação |
|---|-----------|----------|-----------|------|
| E1 | PDF único de documentação | **Atende** | `docs/Documentacao_Mente_Saudavel.pdf` — 18 páginas. | — |
| E2 | Script completo do banco | **Atende** | `database/00_create_database.sql` a `04_seed.sql` (criação, schema, views, procedures e dados de exemplo). | — |
| E3 | Código-fonte com estrutura de pastas | **Atende** | `app/`, `database/`, `docs/`, `postman/`, `scripts/`, `app.py`, `requirements.txt`. | — |
| E4 | ZIP único `[iniciais].[sistema].zip` | **Atende** | `entrega/Jhennyfer_Joao.Mente_Saudavel.zip` — 43 arquivos, 1,78 MB. | — |

---

## 3. O que foi removido por estar fora do escopo da atividade

| Item removido | Motivo |
|---------------|--------|
| `exemplos/` (API de exemplo na porta 5001) | Não faz parte do sistema entregue. |
| `tests/` e `scripts/relatorio_testes.py` | Suíte automatizada não é exigida pela atividade. |
| `docs/testes/`, `docs/RELATORIO_DE_TESTES.md` | Evidências internas de teste, substituídas pelas capturas do Postman no PDF. |
| `scripts/verificar_entrega.py`, `scripts/banco_local.py` | Utilitários internos de verificação e de banco portátil. |
| `api.http`, `.vscode/`, `run.py`, `Procfile` | Atalhos de desenvolvimento e arquivos de deploy, não exigidos. |
| `docs/AUDITORIA-ETAPA-1.md`, `docs/documentacao.md`, `docs/URL_PUBLICA.txt` | Documentos auxiliares e link temporário de demonstração. |
| Tabela `usuarios_exemplo` e banco `mente_saudavel_test` | Resíduos da API de exemplo e dos testes. |
| `gunicorn` em `requirements.txt` | Dependência exclusiva de deploy em produção. |

O banco `mente_saudavel` ficou apenas com as 5 tabelas do sistema
(`psicologos`, `pacientes`, `consultas`, `evolucoes`, `auditoria_pacientes`),
3 views, 4 procedures e 4 funções.

---

## 4. Única pendência: comprovar o duplo check no Git

O requisito diz: *“as atividades de cada integrante deverão ser revisadas por
pelo menos outro membro da equipe”*. Para gerar a evidência no GitHub:

1. Criar uma branch para cada frente (por exemplo `revisao/banco` e
   `revisao/api`).
2. Abrir um Pull Request de cada branch para `main`.
3. **O revisor deve ser o outro integrante** (Jhennyfér revisa o que João Vitor
   escreveu e vice-versa), com pelo menos um comentário de revisão.
4. Fazer o merge e guardar o link dos PRs no PDF ou na apresentação.

Alternativa aceitável: registrar no PDF uma tabela de revisão com data,
artefato revisado, autor e revisor, assinada pelos dois. O ideal é ter as duas
coisas (PR + registro no PDF).

---

## 5. Checklist final de entrega

- [x] Banco normalizado, com PKs, FKs e 18 CHECKs
- [x] Stored procedure usada pela API (3 procedures)
- [x] Procedure de relatório com VIEW + JOIN
- [x] 25 endpoints em JSON
- [x] CRUD completo + listagens + relatórios
- [x] Flask + PostgreSQL
- [x] Configuração centralizada (`app/config.py` + `.env.example`)
- [x] Validações no back-end e no front-end
- [x] PDF único com capa, responsáveis, objetivo, arquitetura, comentários por coluna e capturas legendadas
- [x] ZIP com nome `Jhennyfer_Joao.Mente_Saudavel.zip`
- [ ] Duplo check registrado no GitHub (PRs revisados pelo outro integrante)
- [ ] Importar `postman/mente-saudavel.postman_collection.json` no Postman para a apresentação

---

## 6. Como reproduzir a verificação

```bash
# 1. Subir a API
python app.py

# 2. Conferir a saúde e os endpoints
curl http://localhost:5000/api/health
curl http://localhost:5000/api/pacientes
curl http://localhost:5000/api/relatorios/atendimentos

# 3. Executar a procedure de relatório direto no banco
psql -U postgres -d mente_saudavel \
  -c "CALL sp_relatorio_atendimentos(CURRENT_DATE - 365, CURRENT_DATE, 'relatorio');" \
  -c "FETCH ALL FROM relatorio;"

# 4. Gerar novamente PDF e ZIP
python docs/gerar_documentacao.py
python scripts/gerar_zip.py --membros "Jhennyfer Joao" --saida entrega
```
