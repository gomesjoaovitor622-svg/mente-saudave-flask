# Auditoria — Etapa 1 (diagnóstico técnico)

**Projeto:** `mente-saudave-flask` (`https://github.com/gomesjoaovitor622-svg/mente-saudave-flask`)
**Pasta analisada:** `OneDrive\Documentos\Projeto Padrão\repo`
**Commit de referência:** `5c4d0ce` (branch `main`, com alterações locais não commitadas)
**Data:** 16/11/2026
**Método:** leitura do código-fonte, dos scripts SQL, dos testes e da documentação;
consulta ao catálogo do PostgreSQL em uso; execução real da API e da suíte de testes.
Nenhum arquivo de código do projeto foi alterado nesta etapa.

---

## 1. Inventário

| Grupo | Arquivos | Linhas |
|---|---|---|
| Python da aplicação (`app/`, `app.py`, `run.py`) | 14 | 1.590 |
| Frontend (`app/templates`, `app/static`) | 4 | 1.383 |
| SQL (`database/`) | 5 | 904 |
| Testes (`tests/`) | 4 | 841 |

**Stack:** Python 3.11.9 · Flask 3.1.3 · psycopg2-binary 2.9.13 · python-dotenv 1.2.0 ·
PostgreSQL 18.6 · pytest 8.4.2 · Jinja2 + JavaScript puro.
Não há ORM: o acesso é SQL parametrizado direto (`app/db.py`), com stored procedures
para as regras de negócio.

## 2. Arquitetura

```
app.py / run.py          ponto de entrada (app.run em host 0.0.0.0)
app/__init__.py          application factory: JSON provider, CORS, erros, blueprints
app/config.py            Config / TestingConfig / ProductionConfig (lê .env)
app/db.py                conexão por request em flask.g + helpers query/execute/CALL
app/errors.py            ApiError + handlers (409/422/503/500) centralizados
app/validators.py        validação de entrada (CPF, e-mail, telefone, datas, paginação)
app/routes/*.py          blueprints por domínio (6 módulos)
database/*.sql           schema, views, procedures, seed
tests/*.py               unittest de API, constraints e validadores
```

Pontos corretos: separação de camadas, nenhuma rota abre conexão direto, todo valor vindo
do usuário passa por `%s`/`%(nome)s`, nome de procedure interpolado é constante de código,
erros de banco não vazam para o cliente.

## 3. API — 25 endpoints

| Grupo | Rotas |
|---|---|
| Saúde | `GET /api`, `GET /api/health` |
| Pacientes | `GET /api/pacientes`, `GET /api/pacientes/{id}`, `GET /api/pacientes/{id}/resumo`, `POST`, `PUT`, `DELETE` |
| Psicólogos | `GET`, `GET /{id}`, `POST`, `PUT`, `DELETE` |
| Consultas | `GET`, `GET /{id}`, `POST`, `PUT`, `DELETE` |
| Evoluções | `GET`, `GET /{id}`, `POST`, `PUT`, `DELETE` |
| Relatórios | `GET /api/relatorios/atendimentos`, `GET /api/relatorios/resumo` |

Métodos HTTP usados corretamente (GET/POST/PUT/DELETE), respostas JSON padronizadas,
paginação com teto (`MAX_PAGE_SIZE = 100`).

## 4. Banco de dados (estado real após a migração)

| Tabela | Colunas | Tamanho |
|---|---|---|
| `pacientes` | 12 | 80 kB |
| `psicologos` | 8 | 56 kB |
| `consultas` | 10 | 96 kB |
| `evolucoes` | 6 | 64 kB |
| `auditoria_pacientes` | 6 | 32 kB |

| Objeto | Quantidade |
|---|---|
| Views | 3 (`vw_agenda_completa`, `vw_evolucoes`, `vw_relatorio_atendimentos`) |
| Funções/procedures | 8 (inclui `sp_criar_paciente`, `sp_agendar_consulta`, `sp_registrar_evolucao`, `sp_relatorio_atendimentos` com `refcursor`) |
| PRIMARY KEY | 5 |
| FOREIGN KEY | 3 (`consultas→pacientes`, `consultas→psicologos`, `evolucoes→consultas`) |
| UNIQUE | 5 |
| CHECK | 18 |
| NOT NULL | 33 |
| Índices | 16 (PKs + `idx_pacientes_nome`, `idx_consultas_data`, `idx_consultas_paciente`, `idx_consultas_psicologo`, `idx_evolucoes_criado_em`, `uq_consultas_agenda_ativa`) |

O `uq_consultas_agenda_ativa` é um índice único **parcial**
(`WHERE status <> 'cancelada'`), que impede dois agendamentos ativos no mesmo horário
sem bloquear reagendamento após cancelamento — boa solução.

Dados preservados na migração: 5 pacientes, 3 psicólogos, 7 consultas, 3 evoluções,
8 registros de auditoria.

## 5. Integração verificada (execução real)

| Verificação | Resultado |
|---|---|
| `GET /api/health` | `200` · `{"banco":"mente_saudavel","versao_postgresql":"PostgreSQL 18.6 ..."}` |
| `GET /api/pacientes?per_page=2` | `200` · 2 registros, `total=5`, `total_paginas=3` |
| `GET /api/relatorios/resumo` | `200` · 5 pacientes ativos, 3 psicólogos, 3 consultas agendadas, 3 realizadas, humor médio 7.0 |
| `GET /api` | `200` · 25 endpoints |
| `pytest` (RUN_DB_TESTS=1) | **56 passed** em 10,4 s |

Conclusão: frontend, backend e banco estão corretamente integrados; o que falta é
segurança e governança de dados, não funcionamento.

## 6. Achados

### Críticos

**C1 — Nenhuma autenticação ou autorização.**
As 25 rotas são públicas. Não existe tabela de usuários, sessão, token ou verificação de
perfil (busca por `auth|token|login|senha|session` nas rotas não retorna nada; o schema tem
só as 5 tabelas de domínio). Qualquer processo que alcance a porta lê, cria, altera e exclui
prontuário. Isso viola o requisito da Fase 4 do prompt e a LGPD (art. 46).

**C2 — Exclusão de paciente apaga o prontuário inteiro.**
`app/routes/pacientes.py:276-287` executa `DELETE FROM pacientes`; a FK
`fk_consultas_paciente` é `ON DELETE CASCADE`, então consultas e evoluções somem junto.
Prontuário de saúde tem prazo legal de guarda (CFM 1821/2007: 20 anos) — exclusão física
irreversível é incompatível com isso.

**C3 — Dados clínicos sem proteção adicional.**
`evolucoes.relato` e `pacientes.observacoes` são texto puro; não há criptografia em repouso,
mascaramento ou registro de quem **leu** o prontuário (a trigger só audita escrita em
`pacientes`).

### Altos

**A1 — CORS liberado para qualquer origem.**
`app/__init__.py:101-114` devolve `Access-Control-Allow-Origin: *`. Sem autenticação,
qualquer página web aberta no navegador do usuário pode consumir a API se ela estiver
acessível na rede.

**A2 — Servidor em HTTP puro e em todas as interfaces.**
`app.py:69-77` usa `host="0.0.0.0"` sem TLS e sem proxy reverso no repositório. Credenciais
e dados trafegam em claro na rede local.

**A3 — Segredos com padrão fraco e debug ligado por padrão.**
`app/config.py:51` usa `SECRET_KEY` padrão `chave-de-desenvolvimento`;
`app/config.py:52` define `DEBUG=True` como padrão. Em produção, esquecer a variável abre
o console do Werkzeug.

**A4 — Sem limite de requisições nem trilha de acesso.**
Não há throttling, bloqueio por tentativas, nem log de auditoria de leitura por usuário.

### Médios

| # | Achado | Evidência |
|---|---|---|
| M1 | `scripts/banco_local.py` ainda gerencia o cluster antigo na porta `55433` e **reescreve o `.env`** — rodar `configurar` volta o projeto para o banco legado | `scripts/banco_local.py` (docstring e `configurar`) |
| M2 | Conexão nova por requisição, sem pool | `app/db.py:29-34` |
| M3 | `logger.exception` pode registrar valores de SQL no stack trace | `app/errors.py:96,107` |
| M4 | Testes de integração exigem banco criado à mão + `RUN_DB_TESTS=1`; nada automatiza o setup | `tests/test_api.py:17-20`, `README:347` |
| M5 | CPF em claro (`VARCHAR(11)`), e-mail e telefone sem proteção | `database/01_schema.sql` |
| M6 | Sem rotina de backup automatizado | `database/`, `scripts/` |
| M7 | `00_create_database.sql` usa `\gexec`, exclusivo do `psql` | `database/00_create_database.sql:7-8` |
| M8 | Documentação desatualizada após a migração (descreve o cluster 55433) | `README.md`, `docs/documentacao.md` |

### Baixos

- Duas fontes de verdade para debug: `app/config.py:52` (`DEBUG=True`) e
  `app.py:66` (`FLASK_DEBUG` padrão `0`).
- `entrega/Jhennyfer_Joao.Mente_Saudavel.zip` presente na pasta (ignorado pelo Git).
- Ausência de índice em `consultas(status)` — aceitável, baixa cardinalidade.

### O que está bem feito (manter)

- SQL 100% parametrizado; sem concatenação de valor do usuário.
- Application factory + blueprints + handlers de erro + JSON provider para `date`,
  `Decimal` e `set`.
- 18 CHECK constraints, FKs com política definida, índice único parcial de agenda.
- Regras de negócio nas procedures (idade mínima, CPF único, conflito de agenda).
- Validação de entrada centralizada em `app/validators.py`.
- `.env` fora do versionamento (`.env` no `.gitignore`).
- 56 testes passando contra PostgreSQL real.

## 7. Alteração de infraestrutura feita nesta etapa (com autorização do usuário)

O banco saiu do cluster portátil (`%LOCALAPPDATA%\MenteSaudavel\pgdata-postgres-antigo`,
porta 55433) para o serviço oficial do Windows:

| Item | Antes | Agora |
|---|---|---|
| Instância | cluster do usuário, porta 55433 | serviço `postgresql-x64-18`, porta 5432 |
| Inicialização | manual (`banco_local.py iniciar`) | automática com o Windows |
| Binários | `C:\MenteSaudavel\pgsql\bin` | `C:\Program Files\PostgreSQL\18\bin` |
| Banco da aplicação | `mente_saudavel` (legado) | `mente_saudavel` (migrado) |
| Usuário da aplicação | `postgres` | `joaovitor` (ver nota abaixo) |
| Banco de testes | `mente_saudavel_test` | `mente_saudavel_test` (recriado 01→04) |

Como foi feito: `pg_dump -Fc` do banco legado (63.616 bytes) → `CREATE DATABASE`
com dono `gomesjoaovitor622@gmail` → `pg_restore --no-owner --no-privileges`
conectado como o próprio papel da aplicação (todos os objetos ficaram com o dono correto).
Contagens conferidas antes e depois: 5/3/7/3/8 — nenhuma diferença.

> **Nota (estado final):** depois da migração, a tarefa do VS Code
> `Banco: configurar` foi executada com o usuário `joaovitor`, que recarregou os
> scripts `01→04` e passou a ser o **dono de tabelas, views e funções**. Por
> isso o `.env` e o atalho do banco usam `joaovitor` — é o único papel com
> privilégio nas tabelas. O papel `gomesjoaovitor622@gmail` continua existindo,
> mas sem acesso aos dados. Dados conferidos novamente: 5/3/7/3/8.

`.env` atual (backup do anterior em `.env.bak-antes-do-servico`):

```env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=mente_saudavel
DB_USER=joaovitor
DB_PASSWORD=Joa1045.5
```

Validação: API no ar respondendo às consultas reais e **56 testes passando**.

> O banco `Mente Saúdave` (criado antes, vazio) continua existindo na mesma instância.
> Ele não é usado pelo projeto. Se a intenção era esse nome, o rename é uma decisão
> separada — hoje o projeto usa `mente_saudavel`, nome esperado por scripts, testes e docs.

## 8. Riscos que continuam abertos

1. API sem autenticação (C1) — bloqueia qualquer uso real.
2. Exclusão em cascata do prontuário (C2).
3. Dados clínicos sem criptografia nem auditoria de leitura (C3).
4. `banco_local.py` pode sobrescrever o `.env` e apontar de volta para o banco antigo (M1).
5. Sem backup automático (M6).

## 9. Proposta para a Etapa 2 (diagnóstico consolidado) e Etapa 3 (correções)

Ordem sugerida, do maior risco para o menor:

1. **Autenticação e autorização** (tabela `usuarios`, hash `scrypt`/`pbkdf2`, sessão
   assinada ou JWT, perfis `admin`/`psicologo`/`recepcao`), protegendo todas as rotas.
2. **Soft delete** em `pacientes` e remoção do `ON DELETE CASCADE` do prontuário
   (`consultas`/`evolucoes` passam a `RESTRICT`), com `status`/`excluido_em`.
3. **CORS restrito por origem**, `SECRET_KEY` obrigatória, `DEBUG` desligado por padrão.
4. **Auditoria de leitura** por usuário e registro de acesso a prontuário.
5. **Rate limiting** e cabeçalhos de segurança.
6. **Pool de conexões** (psycopg2 `pool` ou SQLAlchemy engine) e timeouts.
7. **Backup automatizado** (`pg_dump` diário + rotação) e script de restauração testado.
8. **Ajustar `scripts/banco_local.py`** para o serviço (ou desativá-lo) e atualizar README,
   `docs/documentacao.md` e a coleção Postman.
9. **Automatizar o setup do banco de teste** (script único `01→04`) para o CI.

Nenhum desses itens foi executado ainda: a Etapa 1 é somente leitura de código, com a
migração de banco que você autorizou.
