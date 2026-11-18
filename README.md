# 🌿 Mente Saudável — API Flask + PostgreSQL

Sistema de gestão para uma clínica de psicologia, desenvolvido como projeto
integrador das disciplinas **Desenvolvimento Web III** e **Banco de Dados II**
(IFRO — Curso Superior de Tecnologia em Sistemas para Internet).

A aplicação oferece uma **Web API REST em Python/Flask** para o cadastro de
pacientes, psicólogos, consultas e evoluções clínicas, além de um **painel web**
que consome essa API. Os dados são persistidos em **PostgreSQL**, com regras de
integridade, *stored procedures*, *views* com `JOIN`, *triggers* de auditoria e
validação no back-end.

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
- **Documentação** — [`docs/Documentacao_Mente_Saudavel.pdf`](docs/Documentacao_Mente_Saudavel.pdf)
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
│   └── templates/
│       ├── index.html       # painel web
│       └── api.html         # índice de endpoints
├── database/
│   ├── 00_create_database.sql
│   ├── 01_schema.sql        # tabelas, PK/FK, CHECKs, triggers e índices
│   ├── 02_views.sql         # views com JOIN + funções de relatório
│   ├── 03_procedures.sql    # stored procedures
│   ├── 04_seed.sql          # dados de exemplo
│   └── README.md
├── docs/
│   ├── Documentacao_Mente_Saudavel.pdf
│   ├── gerar_documentacao.py
│   └── img/                 # capturas do painel e evidências Postman
├── postman/
│   └── mente-saudavel.postman_collection.json
├── scripts/
│   └── gerar_zip.py         # empacotamento da entrega
├── .env.example
├── app.py                   # ponto de entrada da aplicação
├── requirements.txt
├── requirements-dev.txt     # dependências para gerar o PDF
└── README.md
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
APP_ENV=development
SECRET_KEY=troque-esta-chave
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mente_saudavel
DB_USER=postgres
DB_PASSWORD=sua_senha
CORS_ORIGINS=*
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

---

## 🔌 Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api` | **Índice navegável de todos os endpoints (HTML e JSON)** |
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

- **Normalização** — tabelas `psicologos`, `pacientes`, `consultas`,
  `evolucoes` e `auditoria_pacientes`, sem dados redundantes; a evolução
  referencia apenas a consulta.
- **PKs e FKs** — todas as relações declaradas com `ON DELETE` definido.
- **Check constraints** — 18 regras nomeadas (CPF, e-mail, datas, status,
  duração, humor, valor etc.).
- **Stored procedures**:
  - `sp_criar_paciente` — usada no `POST /api/pacientes`;
  - `sp_agendar_consulta` — usada no `POST /api/consultas` (valida conflito);
  - `sp_registrar_evolucao` — usada no `POST /api/evolucoes`;
  - `sp_relatorio_atendimentos` — relatório com **VIEW + JOIN** e `REFCURSOR`
    (não é chamada pela API, conforme o enunciado).
- **Views** — `vw_agenda_completa`, `vw_evolucoes` e
  `vw_relatorio_atendimentos`, todas com `JOIN`.
- **Auditoria** — trigger registra `INSERT`, `UPDATE` e `DELETE` de pacientes.
- **Agenda** — índice único parcial impede dois agendamentos ativos no mesmo
  horário para o mesmo profissional.
- **Comentários** — todas as colunas das tabelas e views possuem
  `COMMENT ON COLUMN`.

---

## 📮 Postman

Importe `postman/mente-saudavel.postman_collection.json` no Postman
(**Import → File**, ou arraste o arquivo para a janela). A variável `baseUrl`
já aponta para `http://localhost:5000`. A coleção contém as 25 requisições da
API, organizadas em pastas, e pode ser usada para gerar as capturas exigidas
na documentação.

---

## 📦 Empacotamento e entrega (ZIP)

A entrega é um único arquivo ZIP com o script SQL, o código-fonte e o PDF. O
nome segue a regra da atividade:

```text
[nome inicial de cada membro separado por _].[nome do sistema].zip
```

Para esta entrega (Jhennyfér e João Vitor):

```bash
python scripts/gerar_zip.py --membros "Jhennyfer Joao" --saida entrega
# gera: entrega/Jhennyfer_Joao.Mente_Saudavel.zip
```

O script inclui `app/`, `database/`, `docs/`, `postman/`, `scripts/` e os
arquivos da raiz, ignorando `.venv/`, `.git/`, caches, `.env` e arquivos
temporários.

---

## 👥 Equipe

| Integrante | Banco de Dados II | Desenvolvimento Web III | Documentação e entrega |
|------------|-------------------|-------------------------|------------------------|
| **Jhennyfér** | Modelagem e normalização; `01_schema.sql`; CHECK/FK/UNIQUE, triggers e índices; views com JOIN (`02_views.sql`) e funções de relatório | Apoio a `app/db.py` e às chamadas de procedures; tabela de endpoints e coleção Postman | Comentários coluna a coluna, constraints e views; PDF final e ZIP |
| **João Vitor** | Stored procedures (`03_procedures.sql`) e seed (`04_seed.sql`) | API Flask, blueprints, validações e erros; painel web e integração via `fetch` | Capturas de tela, evidências Postman e revisão do script SQL |

> Cada entrega é revisada pelo outro integrante (duplo check).

---

## 📄 Licença

Projeto acadêmico desenvolvido para fins de avaliação no IFRO.
