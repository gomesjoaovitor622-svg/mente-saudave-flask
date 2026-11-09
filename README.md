# 🌿 Mente Saudável — API Flask + PostgreSQL

Sistema de gestão para uma clínica de psicologia, desenvolvido como projeto
integrador das disciplinas **Desenvolvimento Web III** e **Banco de Dados II**
(IFRO — Curso Superior de Tecnologia em Sistemas para Internet).

A aplicação oferece uma **Web API REST em Python/Flask** para o cadastro de
pacientes, psicólogos, consultas e evoluções clínicas, além de um **painel web**
que consome essa API. Os dados são persistidos em **PostgreSQL**, com regras de
integridade, *stored procedures*, *views* com `JOIN`, *triggers* de auditoria e
validação em todas as camadas.

---

## 🧩 Funcionalidades

- **Pacientes** — CRUD completo, busca por nome, filtro por status e resumo
  individual (consultas, humor médio e última consulta).
- **Psicólogos** — CRUD completo com CRP, especialidade e valor da sessão.
- **Consultas** — agendamento (com verificação de conflito de horário),
  listagem, atualização de status e exclusão.
- **Evoluções** — registro do prontuário (humor de 1 a 10 e relato da sessão).
- **Relatórios** — atendimentos por período e indicadores gerais da clínica.
- **Painel web** — dashboard, tabelas e formulários consumindo a API via `fetch`.
- **Documentação** — [`docs/Documentacao_Mente_Saudavel.pdf`](docs/Documentacao_Mente_Saudavel.pdf),
  relatório de testes em [`docs/RELATORIO_DE_TESTES.md`](docs/RELATORIO_DE_TESTES.md)
  e coleção do Postman em [`postman/`](postman/).

---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|--------|------------|
| Linguagem | Python 3.10+ |
| Framework web | Flask 3 |
| Banco de dados | PostgreSQL 14+ |
| Driver | psycopg2 |
| Configuração | python-dotenv (`.env`) |
| Frontend | HTML, CSS e JavaScript puro |
| Testes | pytest |

---

## 📁 Estrutura do projeto

```text
mente-saudave-flask/
├── app/
│   ├── __init__.py          # factory da aplicação Flask (CORS, JSON, erros)
│   ├── config.py            # configurações centralizadas (.env)
│   ├── db.py                # conexão e helpers de acesso ao PostgreSQL
│   ├── errors.py            # tratamento de erros em JSON
│   ├── validators.py        # validações de CPF, e-mail, datas, etc.
│   ├── routes/
│   │   ├── health.py
│   │   ├── pacientes.py
│   │   ├── psicologos.py
│   │   ├── consultas.py
│   │   ├── evolucoes.py
│   │   └── relatorios.py
│   ├── static/
│   │   ├── css/styles.css
│   │   └── js/app.js
│   └── templates/index.html
├── database/
│   ├── 00_create_database.sql
│   ├── 01_schema.sql        # tabelas, PK/FK, checks, triggers e índices
│   ├── 02_views.sql         # views com JOIN + funções de relatório
│   ├── 03_procedures.sql    # stored procedures
│   ├── 04_seed.sql          # dados de exemplo
│   └── README.md
├── docs/
│   ├── Documentacao_Mente_Saudavel.pdf
│   ├── RELATORIO_DE_TESTES.md
│   ├── documentacao.md
│   ├── gerar_documentacao.py
│   ├── img/                 # capturas do painel e evidências Postman
│   └── testes/              # harness HTTP, JSON de resultados e HTML estilo Postman
├── postman/
│   └── mente-saudavel.postman_collection.json
├── scripts/
│   ├── relatorio_testes.py  # bateria HTTP + CHECK constraints com evidências
│   └── gerar_zip.py         # empacotamento da entrega
├── tests/
│   ├── conftest.py
│   ├── test_validators.py
│   ├── test_api.py
│   └── test_constraints.py  # integridade do banco (CHECK, FK, UNIQUE, triggers...)
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── app.py                   # ponto de entrada oficial
└── run.py                   # compatibilidade (delega para app.py)
```

---

## 🚀 Como executar

### 1. Pré-requisitos

- Python 3.10 ou superior
- PostgreSQL 14 ou superior em execução

### 2. Criar o ambiente virtual e instalar dependências

```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configurar as variáveis de ambiente

```bash
copy .env.example .env    # Windows
cp .env.example .env      # Linux/macOS
```

Edite o `.env` com os dados do seu PostgreSQL:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mente_saudavel
DB_USER=postgres
DB_PASSWORD=sua_senha
```

### 4. Criar e popular o banco

```bash
psql -U postgres -f database/00_create_database.sql
psql -U postgres -d mente_saudavel -f database/01_schema.sql
psql -U postgres -d mente_saudavel -f database/02_views.sql
psql -U postgres -d mente_saudavel -f database/03_procedures.sql
psql -U postgres -d mente_saudavel -f database/04_seed.sql
```

> Também é possível executar os arquivos pelo pgAdmin (Query Tool), um por vez.
> Detalhes em [`database/README.md`](database/README.md).

### 5. Iniciar a aplicação

```bash
python app.py
```

- Painel web: <http://localhost:5000>
- API: <http://localhost:5000/api>
- Health check: <http://localhost:5000/api/health>

> `app.py` é o ponto de entrada oficial. `run.py` continua funcionando por
> compatibilidade e delega para o mesmo código.

### 6. Demonstração pública (temporária)

Enquanto o servidor Flask, o PostgreSQL e o túnel Cloudflare estiverem em
execução na máquina de demonstração, o sistema pode ser acessado em:

**<https://strategic-beam-kirk-mostly.trycloudflare.com>**

O endereço também é gravado em [`docs/URL_PUBLICA.txt`](docs/URL_PUBLICA.txt)
e usado na geração do PDF. Como é um túnel gratuito `trycloudflare.com`, ele
não possui garantia de disponibilidade e deixa de responder quando os
processos são encerrados.

---

## 🔌 Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/health` | Status da API e do banco |
| GET | `/api/pacientes` | Lista pacientes (`page`, `per_page`, `nome`, `status`, `cidade`) |
| GET | `/api/pacientes/{id}` | Busca paciente por id |
| GET | `/api/pacientes/{id}/resumo` | Resumo do paciente (consultas e humor) |
| POST | `/api/pacientes` | Cadastra paciente (**stored procedure**) |
| PUT | `/api/pacientes/{id}` | Atualiza paciente |
| DELETE | `/api/pacientes/{id}` | Remove paciente |
| GET | `/api/psicologos` | Lista psicólogos |
| GET | `/api/psicologos/{id}` | Busca psicólogo |
| POST | `/api/psicologos` | Cadastra psicólogo |
| PUT | `/api/psicologos/{id}` | Atualiza psicólogo |
| DELETE | `/api/psicologos/{id}` | Remove psicólogo |
| GET | `/api/consultas` | Lista consultas (`status`, `id_paciente`, `id_psicologo`, datas) |
| GET | `/api/consultas/{id}` | Busca consulta |
| POST | `/api/consultas` | Agenda consulta (**stored procedure**) |
| PUT | `/api/consultas/{id}` | Atualiza consulta |
| DELETE | `/api/consultas/{id}` | Remove consulta |
| GET | `/api/evolucoes` | Lista evoluções (`id_paciente`, `id_consulta`) |
| GET | `/api/evolucoes/{id}` | Busca evolução |
| POST | `/api/evolucoes` | Registra evolução (**stored procedure**) |
| PUT | `/api/evolucoes/{id}` | Atualiza evolução |
| DELETE | `/api/evolucoes/{id}` | Remove evolução |
| GET | `/api/relatorios/atendimentos` | Relatório por período (`data_inicio`, `data_fim`) |
| GET | `/api/relatorios/resumo` | Indicadores gerais |

### Exemplo de requisição

```http
POST /api/pacientes
Content-Type: application/json

{
  "nome": "Ana Beatriz Souza",
  "cpf": "52998224725",
  "email": "ana.souza@email.com",
  "telefone": "(69) 99999-1234",
  "data_nascimento": "1994-03-18",
  "genero": "feminino",
  "cidade": "Porto Velho"
}
```

Resposta `201 Created`:

```json
{
  "mensagem": "Paciente Ana Beatriz Souza cadastrado com sucesso (id 6).",
  "dados": {
    "id_paciente": 6,
    "nome": "Ana Beatriz Souza",
    "cpf": "52998224725",
    "status": "ativo",
    "criado_em": "2026-11-05T21:10:00-04:00"
  }
}
```

### Formato dos erros

```json
{
  "erro": true,
  "mensagem": "CPF invalido: digitos verificadores nao conferem.",
  "status": 422,
  "detalhes": { "campos": ["cpf"] }
}
```

---

## 🗄️ Destaques do banco de dados

- **Normalização** — tabelas `psicologos`, `pacientes`, `consultas` e
  `evolucoes`, sem dados redundantes; a evolução referencia apenas a consulta.
- **PKs e FKs** — todas as relações declaradas com `ON DELETE` definido.
- **Check constraints** — mais de 20 regras (CPF, e-mail, datas, status,
  duração, humor, valor etc.).
- **Stored procedures**:
  - `sp_criar_paciente` — usada no `POST /api/pacientes`;
  - `sp_agendar_consulta` — usada no `POST /api/consultas` (valida conflito);
  - `sp_registrar_evolucao` — usada no `POST /api/evolucoes`;
  - `sp_relatorio_atendimentos` — relatório com **VIEW + JOIN** e `REFCURSOR`
    (não é chamada pela API, conforme o enunciado).
- **View de relatório** — `vw_relatorio_atendimentos` combina consultas,
  pacientes, psicólogos e evoluções.
- **Auditoria** — trigger registra `INSERT`, `UPDATE` e `DELETE` de pacientes.
- **Agenda** — índice único parcial impede dois agendamentos ativos no mesmo
  horário para o mesmo profissional.

---

## ✅ Testes

A suíte possui **55 testes** e cobre validações unitárias, integração dos
endpoints e integridade do banco de dados.

Testes unitários (não precisam de banco):

```bash
pytest tests/test_validators.py -q
```

Testes de integração e de integridade (usam um banco de teste):

```bash
# 1. crie o banco mente_saudavel_test e execute os scripts 01 a 04 nele
# 2. defina as variáveis e rode:
set RUN_DB_TESTS=1
set TEST_DB_NAME=mente_saudavel_test
pytest -q
```

No Linux/macOS:

```bash
RUN_DB_TESTS=1 TEST_DB_NAME=mente_saudavel_test pytest -q
```

Resultado esperado:

```text
55 passed
```

### Evidências dos testes

O script `scripts/relatorio_testes.py` executa a API real e grava evidências
com payload, status HTTP e verificação no banco:

```bash
python scripts/relatorio_testes.py --base-url http://127.0.0.1:5000
```

Ele gera:

- [`docs/RELATORIO_DE_TESTES.md`](docs/RELATORIO_DE_TESTES.md) — relatório detalhado;
- [`docs/testes/resultado_testes.json`](docs/testes/resultado_testes.json) — evidência legível por máquina;
- páginas HTML no estilo Postman em [`docs/testes/`](docs/testes/).

Resultado da última execução: **22/22 testes HTTP** com o status esperado e
**8/8 CHECK constraints** rejeitando dados inválidos por SQL direto.

---

## 📮 Postman

Importe `postman/mente-saudavel.postman_collection.json` no Postman. A variável
`baseUrl` já aponta para `http://localhost:5000`. A coleção contém exemplos de
todas as operações e pode ser usada para gerar as capturas de tela exigidas na
documentação.

As capturas usadas no PDF são geradas a partir das execuções reais:

```bash
python docs/testes/gerar_postman_html.py
```

---

## 📦 Empacotamento e entrega (ZIP)

A entrega é um único arquivo ZIP com o script SQL, o código-fonte e o PDF. O
nome segue a regra da atividade:

```text
[nome inicial de cada membro separado por _].[nome do sistema].zip
```

Exemplo com quatro integrantes (João, Maria, Pedro e Ana):

```text
Joao_Maria_Pedro_Ana.Mente_Saudavel.zip
```

Gere o pacote automaticamente com:

```bash
python scripts/gerar_zip.py --membros "Joao Maria Pedro Ana"
```

O script inclui `app/`, `database/`, `docs/`, `postman/`, `scripts/`, `tests/`
e os arquivos da raiz, ignorando `.venv/`, `.git/`, caches, `.env` e arquivos
temporários.

---

## 👥 Equipe

| Integrante | Banco de Dados II | Desenvolvimento Web III | Documentação e testes |
|------------|-------------------|-------------------------|-----------------------|
| _(preencher)_ | Modelagem, `01_schema.sql`, CHECK/FK/UNIQUE, triggers e índices | Apoio a `app/db.py` e às chamadas de procedures | Comentários das colunas e constraints |
| _(preencher)_ | Views com JOIN (`02_views.sql`) e funções de relatório | API Flask, blueprints, validações e erros | Tabela de endpoints e coleção Postman |
| _(preencher)_ | Stored procedures (`03_procedures.sql`) e seed (`04_seed.sql`) | Painel web (HTML/CSS/JS) e integração via `fetch` | Capturas de tela do painel e evidências |
| _(preencher)_ | Testes de integridade (`tests/test_constraints.py`) | Testes de API (`tests/test_api.py`) e validadores | Relatório de testes, PDF e ZIP |

> Substitua os nomes acima pelos integrantes da equipe antes da entrega. Cada
> entrega deve ser revisada por pelo menos outro integrante (duplo check).

---

## 📄 Licença

Projeto acadêmico desenvolvido para fins de avaliação no IFRO.
