# Relatorio de Testes - Mente Saudavel

**Data de execucao:** 2026-11-08T20:45:48  
**API testada:** `http://127.0.0.1:5055`  
**Banco de dados:** `mente_saudavel` em `127.0.0.1:55432`  
**Responsavel:** equipe Mente Saudavel (IFRO)

## 1. Resumo

| Indicador | Resultado |
|---|---|
| Testes HTTP executados | 22 |
| Testes HTTP com status esperado | 22 |
| CHECK constraints testadas | 8 |
| Constraints que rejeitaram o dado invalido | 8 |

> Todos os testes foram executados contra a API real, com PostgreSQL ativo. O efeito de cada operacao foi conferido por consulta direta ao banco.

## 2. Testes de endpoints (HTTP)

| # | Metodo | Rota | Status | Esperado | Resultado | Comportamento no banco |
|---|---|---|---|---|---|---|
| 1 | GET | `/api/health` | 200 | 200 | OK | Executa SELECT current_database(), version(); nenhuma escrita. |
| 2 | POST | `/api/pacientes` | 201 | 201 | OK | INSERT em pacientes pela procedure; trigger trg_auditar_paciente grava linha INSERT em auditoria_pacientes. |
| 3 | POST | `/api/pacientes` | 409 | 409 | OK | A procedure detecta duplicidade antes do INSERT; nenhuma linha nova. |
| 4 | GET | `/api/pacientes?nome=Paciente Relatorio` | 200 | 200 | OK | SELECT paginado com ILIKE; nao altera dados. |
| 5 | GET | `/api/pacientes/11` | 200 | 200 | OK | SELECT por chave primaria. |
| 6 | PUT | `/api/pacientes/11` | 200 | 200 | OK | UPDATE em pacientes; trigger preenche atualizado_em; auditoria grava UPDATE. |
| 7 | PUT | `/api/pacientes/11` | 422 | 422 | OK | Validacao do Flask interrompe antes do banco; nenhuma alteracao. |
| 8 | POST | `/api/psicologos` | 201 | 201 | OK | INSERT em psicologos com CRP/e-mail unicos. |
| 9 | GET | `/api/psicologos?especialidade=Psicologia Clinica` | 200 | 200 | OK | SELECT com ILIKE e paginacao. |
| 10 | POST | `/api/consultas` | 201 | 201 | OK | INSERT em consultas pela procedure; valor recebe o padrao do psicologo quando omitido; indice unico parcial protege o horario. |
| 11 | POST | `/api/consultas` | 409 | 409 | OK | A procedure e o indice uq_consultas_agenda_ativa impedem o segundo agendamento ativo; nenhuma linha nova. |
| 12 | POST | `/api/evolucoes` | 201 | 201 | OK | INSERT em evolucoes (1:1 com a consulta). |
| 13 | POST | `/api/evolucoes` | 409 | 409 | OK | A procedure recusa a segunda evolucao; UNIQUE em id_consulta e a ultima barreira. |
| 14 | GET | `/api/consultas?status=agendada` | 200 | 200 | OK | SELECT na view vw_agenda_completa (JOIN de 3 tabelas). |
| 15 | GET | `/api/evolucoes?id_consulta=11` | 200 | 200 | OK | SELECT na view vw_evolucoes (JOIN de 4 tabelas). |
| 16 | GET | `/api/pacientes/11/resumo` | 200 | 200 | OK | Funcao tabular agrega consultas, realizadas, agendadas e humor medio. |
| 17 | GET | `/api/relatorios/atendimentos?data_inicio=2000-01-01&data_fim=2100-12-31` | 200 | 200 | OK | SELECT na funcao fn_relatorio_atendimentos, que le a view vw_relatorio_atendimentos. |
| 18 | GET | `/api/relatorios/resumo` | 200 | 200 | OK | Agregacoes (COUNT/AVG) e agrupamento por especialidade. |
| 19 | DELETE | `/api/consultas/11` | 200 | 200 | OK | DELETE em consultas; FK ON DELETE CASCADE remove a evolucao. |
| 20 | DELETE | `/api/pacientes/11` | 200 | 200 | OK | DELETE em pacientes; auditoria grava DELETE. |
| 21 | DELETE | `/api/psicologos/6` | 200 | 200 | OK | DELETE em psicologos (sem consultas vinculadas). |
| 22 | GET | `/api/pacientes/11` | 404 | 404 | OK | Nenhuma linha encontrada; handler devolve JSON padronizado. |

## 3. Detalhamento dos testes HTTP

### 3.1 Health check (API + PostgreSQL)

- **Requisicao:** `GET /api/health`
- **Status HTTP:** `200` (esperado `200`)
- **Comportamento no banco:** Executa SELECT current_database(), version(); nenhuma escrita.
- **Verificacao no banco:** banco conectado: mente_saudavel

**Resposta recebida**

```json
{
  "status": "ok",
  "servico": "Mente Saudavel API",
  "banco": "mente_saudavel",
  "versao_postgresql": "PostgreSQL 18.6 on x86_64-windows"
}
```

### 3.2 Criar paciente (sp_criar_paciente)

- **Requisicao:** `POST /api/pacientes`
- **Status HTTP:** `201` (esperado `201`)
- **Comportamento no banco:** INSERT em pacientes pela procedure; trigger trg_auditar_paciente grava linha INSERT em auditoria_pacientes.
- **Verificacao no banco:** paciente no banco: 1

**Payload enviado**

```json
{
  "nome": "Paciente Relatorio de Testes",
  "cpf": "55529237070",
  "email": "relatorio.55529237070@email.com",
  "telefone": "(69) 99999-4242",
  "data_nascimento": "1994-03-18",
  "genero": "nao_informado",
  "cidade": "Porto Velho",
  "observacoes": "Registro criado pelo script de relatorio de testes."
}
```

**Resposta recebida**

```json
{
  "mensagem": "Paciente Paciente Relatorio de Testes cadastrado com sucesso (id 11).",
  "dados": {
    "id_paciente": 11,
    "nome": "Paciente Relatorio de Testes",
    "cpf": "55529237070",
    "email": "relatorio.55529237070@email.com",
    "telefone": "(69) 99999-4242",
    "data_nascimento": "1994-03-18",
    "genero": "nao_informado",
    "cidade": "Porto Velho",
    "observacoes": "Registro criado pelo script de relatorio de testes.",
    "status": "ativo",
    "criado_em": "2026-11-08T20:45:45.548994-04:00",
    "atualizado_em": null
  }
}
```

### 3.3 Tentar cadastrar CPF duplicado

- **Requisicao:** `POST /api/pacientes`
- **Status HTTP:** `409` (esperado `409`)
- **Comportamento no banco:** A procedure detecta duplicidade antes do INSERT; nenhuma linha nova.
- **Verificacao no banco:** pacientes com o CPF: 1

**Payload enviado**

```json
{
  "nome": "Paciente Relatorio de Testes",
  "cpf": "55529237070",
  "email": "relatorio.55529237070@email.com",
  "telefone": "(69) 99999-4242",
  "data_nascimento": "1994-03-18",
  "genero": "nao_informado",
  "cidade": "Porto Velho",
  "observacoes": "Registro criado pelo script de relatorio de testes."
}
```

**Resposta recebida**

```json
{
  "erro": true,
  "mensagem": "Ja existe um paciente cadastrado com este CPF.",
  "status": 409
}
```

### 3.4 Listar pacientes com filtro por nome

- **Requisicao:** `GET /api/pacientes?nome=Paciente Relatorio`
- **Status HTTP:** `200` (esperado `200`)
- **Comportamento no banco:** SELECT paginado com ILIKE; nao altera dados.
- **Verificacao no banco:** encontrados no banco: 2

**Resposta recebida**

```json
{
  "dados": [
    {
      "id_paciente": 6,
      "nome": "Paciente Relatorio de Testes",
      "cpf": "19420195724",
      "email": "relatorio.19420195724@email.com",
      "telefone": "(69) 99999-4242",
      "data_nascimento": "1994-03-18",
      "genero": "nao_informado",
      "cidade": "Porto Velho",
      "observacoes": "Registro criado pelo script de relatorio de testes.",
      "status": "ativo",
      "criado_em": "2026-11-07T22:36:49.273511-04:00",
      "atualizado_em": null
    },
    {
      "id_paciente": 11,
      "nome": "Paciente Relatorio de Testes",
      "cpf": "55529237070",
      "email": "relatorio.55529237070@email.com",
      "telefone": "(69) 99999-4242",
      "data_nascimento": "1994-03-18",
      "genero": "nao_informado",
      "cidade": "Porto Velho",
      "observacoes": "Registro criado pelo script de relatorio de testes.",
      "status": "ativo",
      "criado_em": "2026-11-08T20:45:45.548994-04:00",
      "atualizado_em": null
    }
  ],
  "paginacao": {
    "pagina": 1,
    "por_pagina": 10,
    "total": 2,
    "total_paginas": 1
  }
}
```

### 3.5 Obter paciente por id

- **Requisicao:** `GET /api/pacientes/11`
- **Status HTTP:** `200` (esperado `200`)
- **Comportamento no banco:** SELECT por chave primaria.

**Resposta recebida**

```json
{
  "id_paciente": 11,
  "nome": "Paciente Relatorio de Testes",
  "cpf": "55529237070",
  "email": "relatorio.55529237070@email.com",
  "telefone": "(69) 99999-4242",
  "data_nascimento": "1994-03-18",
  "genero": "nao_informado",
  "cidade": "Porto Velho",
  "observacoes": "Registro criado pelo script de relatorio de testes.",
  "status": "ativo",
  "criado_em": "2026-11-08T20:45:45.548994-04:00",
  "atualizado_em": null
}
```

### 3.6 Atualizar cidade do paciente (PUT parcial)

- **Requisicao:** `PUT /api/pacientes/11`
- **Status HTTP:** `200` (esperado `200`)
- **Comportamento no banco:** UPDATE em pacientes; trigger preenche atualizado_em; auditoria grava UPDATE.
- **Verificacao no banco:** cidade atual: Ji-Parana

**Payload enviado**

```json
{
  "cidade": "Ji-Parana"
}
```

**Resposta recebida**

```json
{
  "mensagem": "Paciente atualizado com sucesso.",
  "dados": {
    "id_paciente": 11,
    "nome": "Paciente Relatorio de Testes",
    "cpf": "55529237070",
    "email": "relatorio.55529237070@email.com",
    "telefone": "(69) 99999-4242",
    "data_nascimento": "1994-03-18",
    "genero": "nao_informado",
    "cidade": "Ji-Parana",
    "observacoes": "Registro criado pelo script de relatorio de testes.",
    "status": "ativo",
    "criado_em": "2026-11-08T20:45:45.548994-04:00",
    "atualizado_em": "2026-11-08T20:45:46.094201-04:00"
  }
}
```

### 3.7 Rejeitar CPF invalido no PUT

- **Requisicao:** `PUT /api/pacientes/11`
- **Status HTTP:** `422` (esperado `422`)
- **Comportamento no banco:** Validacao do Flask interrompe antes do banco; nenhuma alteracao.
- **Verificacao no banco:** CPF permanece: 55529237070

**Payload enviado**

```json
{
  "cpf": "12345678900"
}
```

**Resposta recebida**

```json
{
  "erro": true,
  "mensagem": "CPF invalido: digitos verificadores nao conferem.",
  "status": 422
}
```

### 3.8 Criar psicologo

- **Requisicao:** `POST /api/psicologos`
- **Status HTTP:** `201` (esperado `201`)
- **Comportamento no banco:** INSERT em psicologos com CRP/e-mail unicos.
- **Verificacao no banco:** psicologos com CRP: 1

**Payload enviado**

```json
{
  "nome": "Psicologo Relatorio 28153",
  "crp": "06/28153",
  "email": "psi.relatorio.28153@email.com",
  "especialidade": "Psicologia Clinica",
  "valor_sessao": 195.0
}
```

**Resposta recebida**

```json
{
  "mensagem": "Psicologo cadastrado com sucesso.",
  "dados": {
    "id_psicologo": 6,
    "nome": "Psicologo Relatorio 28153",
    "crp": "06/28153",
    "email": "psi.relatorio.28153@email.com",
    "especialidade": "Psicologia Clinica",
    "valor_sessao": 195.0,
    "ativo": true,
    "criado_em": "2026-11-08T20:45:46.205011-04:00"
  }
}
```

### 3.9 Listar psicologos por especialidade

- **Requisicao:** `GET /api/psicologos?especialidade=Psicologia Clinica`
- **Status HTTP:** `200` (esperado `200`)
- **Comportamento no banco:** SELECT com ILIKE e paginacao.

**Resposta recebida**

```json
{
  "dados": [
    {
      "id_psicologo": 6,
      "nome": "Psicologo Relatorio 28153",
      "crp": "06/28153",
      "email": "psi.relatorio.28153@email.com",
      "especialidade": "Psicologia Clinica",
      "valor_sessao": 195.0,
      "ativo": true,
      "criado_em": "2026-11-08T20:45:46.205011-04:00"
    }
  ],
  "paginacao": {
    "pagina": 1,
    "por_pagina": 10,
    "total": 1,
    "total_paginas": 1
  }
}
```

### 3.10 Agendar consulta (sp_agendar_consulta)

- **Requisicao:** `POST /api/consultas`
- **Status HTTP:** `201` (esperado `201`)
- **Comportamento no banco:** INSERT em consultas pela procedure; valor recebe o padrao do psicologo quando omitido; indice unico parcial protege o horario.
- **Verificacao no banco:** consultas no horario: 1

**Payload enviado**

```json
{
  "id_paciente": 11,
  "id_psicologo": 6,
  "data_hora": "2027-01-07T14:00:00",
  "duracao_minutos": 50,
  "modalidade": "online",
  "observacoes": "Consulta criada pelo relatorio de testes."
}
```

**Resposta recebida**

```json
{
  "mensagem": "Consulta agendada com sucesso (id 11).",
  "dados": {
    "id_consulta": 11,
    "data_hora": "2027-01-07T14:00:00-04:00",
    "duracao_minutos": 50,
    "modalidade": "online",
    "status": "agendada",
    "valor": 195.0,
    "observacoes": "Consulta criada pelo relatorio de testes.",
    "id_paciente": 11,
    "paciente": "Paciente Relatorio de Testes",
    "paciente_email": "relatorio.55529237070@email.com",
    "id_psicologo": 6,
    "psicologo": "Psicologo Relatorio 28153",
    "crp": "06/28153",
    "especialidade": "Psicologia Clinica"
  }
}
```

### 3.11 Tentar double-booking no mesmo horario

- **Requisicao:** `POST /api/consultas`
- **Status HTTP:** `409` (esperado `409`)
- **Comportamento no banco:** A procedure e o indice uq_consultas_agenda_ativa impedem o segundo agendamento ativo; nenhuma linha nova.
- **Verificacao no banco:** consultas no horario: 1

**Payload enviado**

```json
{
  "id_paciente": 11,
  "id_psicologo": 6,
  "data_hora": "2027-01-07T14:00:00",
  "duracao_minutos": 50,
  "modalidade": "online",
  "observacoes": "Consulta criada pelo relatorio de testes."
}
```

**Resposta recebida**

```json
{
  "erro": true,
  "mensagem": "Horario ja ocupado para este psicologo.",
  "status": 409
}
```

### 3.12 Registrar evolucao (sp_registrar_evolucao)

- **Requisicao:** `POST /api/evolucoes`
- **Status HTTP:** `201` (esperado `201`)
- **Comportamento no banco:** INSERT em evolucoes (1:1 com a consulta).
- **Verificacao no banco:** evolucoes da consulta: 1

**Payload enviado**

```json
{
  "id_consulta": 11,
  "humor": 8,
  "relato": "Paciente relatou melhora significativa do sono e da ansiedade.",
  "encaminhamento": "Manter sessoes semanais."
}
```

**Resposta recebida**

```json
{
  "mensagem": "Evolucao registrada com sucesso (id 7).",
  "dados": {
    "id_evolucao": 7,
    "id_consulta": 11,
    "id_paciente": 11,
    "paciente": "Paciente Relatorio de Testes",
    "psicologo": "Psicologo Relatorio 28153",
    "data_hora": "2027-01-07T14:00:00-04:00",
    "humor": 8,
    "relato": "Paciente relatou melhora significativa do sono e da ansiedade.",
    "encaminhamento": "Manter sessoes semanais.",
    "criado_em": "2026-11-08T20:45:46.888818-04:00"
  }
}
```

### 3.13 Tentar duplicar a evolucao da mesma consulta

- **Requisicao:** `POST /api/evolucoes`
- **Status HTTP:** `409` (esperado `409`)
- **Comportamento no banco:** A procedure recusa a segunda evolucao; UNIQUE em id_consulta e a ultima barreira.
- **Verificacao no banco:** evolucoes da consulta: 1

**Payload enviado**

```json
{
  "id_consulta": 11,
  "humor": 8,
  "relato": "Paciente relatou melhora significativa do sono e da ansiedade.",
  "encaminhamento": "Manter sessoes semanais."
}
```

**Resposta recebida**

```json
{
  "erro": true,
  "mensagem": "Esta consulta ja possui uma evolucao registrada.",
  "status": 409
}
```

### 3.14 Listar consultas agendadas

- **Requisicao:** `GET /api/consultas?status=agendada`
- **Status HTTP:** `200` (esperado `200`)
- **Comportamento no banco:** SELECT na view vw_agenda_completa (JOIN de 3 tabelas).

**Resposta recebida**

```json
{
  "dados": [
    {
      "id_consulta": 11,
      "data_hora": "2027-01-07T14:00:00-04:00",
      "duracao_minutos": 50,
      "modalidade": "online",
      "status": "agendada",
      "valor": 195.0,
      "observacoes": "Consulta criada pelo relatorio de testes.",
      "id_paciente": 11,
      "paciente": "Paciente Relatorio de Testes",
      "paciente_email": "relatorio.55529237070@email.com",
      "id_psicologo": 6,
      "psicologo": "Psicologo Relatorio 28153",
      "crp": "06/28153",
      "especialidade": "Psicologia Clinica"
    },
    {
      "id_consulta": 7,
      "data_hora": "2026-11-10T17:00:00-04:00",
      "duracao_minutos": 50,
      "modalidade": "presencial",
      "status": "agendada",
      "valor": 180.0,
      "observacoes": "Primeira consulta do adolescente.",
      "id_paciente": 5,
      "paciente": "Rafael Nunes Pereira",
      "paciente_email": "rafael.pereira@email.com",
      "id_psicologo": 1,
      "psicologo": "Ana Paula Ribeiro",
      "crp": "06/12345",
      "especialidade": "Terapia Cognitivo-Comportamental"
    },
    {
      "id_consulta": 5,
      "data_hora": "2026-11-08T16:00:00-04:00",
      "duracao_minutos": 50,
      "modalidade": "online",
      "status": "agendada",
      "valor": 200.0,
      "observacoes": null,
      "id_paciente": 4,
      "paciente": "Beatriz Oliveira Costa",
      "paciente_email": "beatriz.costa@email.com",
      "id_psicologo": 2,
      "psicologo": "Carlos Eduardo Lima",
      "crp": "06/54321",
      "especialidade": "Psicanalise"
    },
    {
      "id_consulta": 4,
      "data_hora": "2026-11-07T09:00:00-04:00",
      "duracao_minutos": 60,
      "modalidade": "presencial",
      "status": "agendada",
      "valor": 220.0,
      "observacoes": "Avaliacao neuropsicologica.",
      "id_paciente": 3,
      "paciente": "Lucas Ferreira Gomes",
      "paciente_email": "lucas.gomes@email.com",
      "id_psicologo": 3,
      "psicologo": "Mariana Souza Alves",
      "crp": "06/98765",
      "especialidade": "Neuropsicologia"
    }
  ],
  "paginacao": {
    "pagina": 1,
    "por_pagina": 10,
    "total": 4,
    "total_paginas": 1
  }
}
```

### 3.15 Listar evolucoes da consulta

- **Requisicao:** `GET /api/evolucoes?id_consulta=11`
- **Status HTTP:** `200` (esperado `200`)
- **Comportamento no banco:** SELECT na view vw_evolucoes (JOIN de 4 tabelas).

**Resposta recebida**

```json
{
  "dados": [
    {
      "id_evolucao": 7,
      "id_consulta": 11,
      "id_paciente": 11,
      "paciente": "Paciente Relatorio de Testes",
      "psicologo": "Psicologo Relatorio 28153",
      "data_hora": "2027-01-07T14:00:00-04:00",
      "humor": 8,
      "relato": "Paciente relatou melhora significativa do sono e da ansiedade.",
      "encaminhamento": "Manter sessoes semanais.",
      "criado_em": "2026-11-08T20:45:46.888818-04:00"
    }
  ],
  "paginacao": {
    "pagina": 1,
    "por_pagina": 10,
    "total": 1,
    "total_paginas": 1
  }
}
```

### 3.16 Resumo do paciente (fn_resumo_paciente)

- **Requisicao:** `GET /api/pacientes/11/resumo`
- **Status HTTP:** `200` (esperado `200`)
- **Comportamento no banco:** Funcao tabular agrega consultas, realizadas, agendadas e humor medio.
- **Verificacao no banco:** total de consultas: 1

**Resposta recebida**

```json
{
  "id_paciente": 11,
  "nome": "Paciente Relatorio de Testes",
  "total_consultas": 1,
  "consultas_realizadas": 0,
  "consultas_agendadas": 1,
  "humor_medio": 8.0,
  "ultima_consulta": "2027-01-07T14:00:00-04:00"
}
```

### 3.17 Relatorio de atendimentos por periodo

- **Requisicao:** `GET /api/relatorios/atendimentos?data_inicio=2000-01-01&data_fim=2100-12-31`
- **Status HTTP:** `200` (esperado `200`)
- **Comportamento no banco:** SELECT na funcao fn_relatorio_atendimentos, que le a view vw_relatorio_atendimentos.

**Resposta recebida**

```json
{
  "periodo": {
    "data_inicio": "2000-01-01",
    "data_fim": "2100-12-31"
  },
  "total_registros": 8,
  "dados": [
    {
      "id_consulta": 6,
      "data_hora": "2026-10-16T11:00:00-04:00",
      "status": "cancelada",
      "modalidade": "presencial",
      "valor": 220.0,
      "id_paciente": 2,
      "paciente": "Maria Clara Santos",
      "id_psicologo": 3,
      "psicologo": "Mariana Souza Alves",
      "especialidade": "Neuropsicologia",
      "humor": null,
      "relato": null
    },
    {
      "id_consulta": 1,
      "data_hora": "2026-10-24T14:00:00-04:00",
      "status": "realizada",
      "modalidade": "presencial",
      "valor": 180.0,
      "id_paciente": 1,
      "paciente": "Joao Pedro Martins",
      "id_psicologo": 1,
      "psicologo": "Ana Paula Ribeiro",
      "especialidade": "Terapia Cognitivo-Comportamental",
      "humor": 6,
      "relato": "Paciente relatou ansiedade no trabalho e dificuldade para dormir. Foram trabalhadas tecnicas de respiracao."
    },
    {
      "id_consulta": 2,
      "data_hora": "2026-10-27T10:00:00-04:00",
      "status": "realizada",
      "modalidade": "online",
      "valor": 200.0,
      "id_paciente": 2,
      "paciente": "Maria Clara Santos",
      "id_psicologo": 2,
      "psicologo": "Carlos Eduardo Lima",
      "especialidade": "Psicanalise",
      "humor": 7,
      "relato": "Boa adesao ao tratamento. Paciente identificou situacoes que despertam preocupacao excessiva."
    },
    {
      "id_consulta": 3,
      "data_hora": "2026-11-01T15:00:00-04:00",
      "status": "realizada",
      "modalidade": "presencial",
      "valor": 180.0,
      "id_paciente": 1,
      "paciente": "Joao Pedro Martins",
      "id_psicologo": 1,
      "psicologo": "Ana Paula Ribeiro",
      "especialidade": "Terapia Cognitivo-Comportamental",
      "humor": 8,
      "relato": "Evolucao positiva. Paciente relata melhora no sono e maior controle da ansiedade."
    },
    {
      "id_consulta": 4,
      "data_hora": "2026-11-07T09:00:00-04:00",
      "status": "agendada",
      "modalidade": "presencial",
      "valor": 220.0,
      "id_paciente": 3,
      "paciente": "Lucas Ferreira Gomes",
      "id_psicologo": 3,
      "psicologo": "Mariana Souza Alves",
      "especialidade": "Neuropsicologia",
      "humor": null,
      "relato": null
    },
    {
      "id_consulta": 5,
      "data_hora": "2026-11-08T16:00:00-04:00",
      "status": "agendada",
      "modalidade": "online",
      "valor": 200.0,
      "id_paciente": 4,
      "paciente": "Beatriz Oliveira Costa",
      "id_psicologo": 2,
      "psicologo": "Carlos Eduardo Lima",
      "especialidade": "Psicanalise",
      "humor": null,
      "relato": null
    },
    {
      "id_consulta": 7,
      "data_hora": "2026-11-10T17:00:00-04:00",
      "status": "agendada",
      "modalidade": "presencial",
      "valor": 180.0,
      "id_paciente": 5,
      "paciente": "Rafael Nunes Pereira",
      "id_psicologo": 1,
      "psicologo": "Ana Paula Ribeiro",
      "especialidade": "Terapia Cognitivo-Comportamental",
      "humor": null,
      "relato": null
    },
    {
      "id_consulta": 11,
      "data_hora": "2027-01-07T14:00:00-04:00",
      "status": "agendada",
      "modalidade": "online",
      "valor": 195.0,
      "id_paciente": 11,
      "paciente": "Paciente Relatorio de Testes",
      "id_psicologo": 6,
      "psicologo": "Psicologo Relatorio 28153",
      "especialidade": "Psicologia Clinica",
      "humor": 8,
      "relato": "Paciente relatou melhora significativa do sono e da ansiedade."
    }
  ]
}
```

### 3.18 Indicadores gerais do painel

- **Requisicao:** `GET /api/relatorios/resumo`
- **Status HTTP:** `200` (esperado `200`)
- **Comportamento no banco:** Agregacoes (COUNT/AVG) e agrupamento por especialidade.

**Resposta recebida**

```json
{
  "totais": {
    "pacientes_ativos": 7,
    "psicologos_ativos": 4,
    "consultas_agendadas": 4,
    "consultas_realizadas": 3,
    "humor_medio": 7.3
  },
  "consultas_por_especialidade": [
    {
      "especialidade": "Terapia Cognitivo-Comportamental",
      "total_consultas": 3
    },
    {
      "especialidade": "Neuropsicologia",
      "total_consultas": 2
    },
    {
      "especialidade": "Psicanalise",
      "total_consultas": 2
    },
    {
      "especialidade": "Psicologia Clinica",
      "total_consultas": 1
    }
  ]
}
```

### 3.19 Excluir consulta (CASCADE na evolucao)

- **Requisicao:** `DELETE /api/consultas/11`
- **Status HTTP:** `200` (esperado `200`)
- **Comportamento no banco:** DELETE em consultas; FK ON DELETE CASCADE remove a evolucao.
- **Verificacao no banco:** evolucoes restantes: 0

**Resposta recebida**

```json
{
  "mensagem": "Consulta removida com sucesso."
}
```

### 3.20 Excluir paciente

- **Requisicao:** `DELETE /api/pacientes/11`
- **Status HTTP:** `200` (esperado `200`)
- **Comportamento no banco:** DELETE em pacientes; auditoria grava DELETE.
- **Verificacao no banco:** paciente restante: 0

**Resposta recebida**

```json
{
  "mensagem": "Paciente removido com sucesso."
}
```

### 3.21 Excluir psicologo

- **Requisicao:** `DELETE /api/psicologos/6`
- **Status HTTP:** `200` (esperado `200`)
- **Comportamento no banco:** DELETE em psicologos (sem consultas vinculadas).
- **Verificacao no banco:** psicologo restante: 0

**Resposta recebida**

```json
{
  "mensagem": "Psicologo removido com sucesso."
}
```

### 3.22 Buscar paciente removido (404)

- **Requisicao:** `GET /api/pacientes/11`
- **Status HTTP:** `404` (esperado `404`)
- **Comportamento no banco:** Nenhuma linha encontrada; handler devolve JSON padronizado.

**Resposta recebida**

```json
{
  "erro": true,
  "mensagem": "Paciente nao encontrado.",
  "status": 404
}
```

## 4. Validacao das CHECK constraints no banco

As tentativas abaixo foram feitas por **SQL direto** (sem passar pela API), comprovando que a integridade e garantida pelo proprio PostgreSQL.

| Constraint | Dado invalido testado | SQLSTATE | Resultado |
|---|---|---|---|
| `ck_pacientes_cpf_formato` | CPF com letras | `23514` | REJEITADO |
| `ck_pacientes_nascimento` | Data de nascimento futura | `23514` | REJEITADO |
| `ck_pacientes_genero` | Genero fora do dominio | `23514` | REJEITADO |
| `ck_consultas_duracao` | Duracao de 10 minutos | `23514` | REJEITADO |
| `ck_consultas_modalidade` | Modalidade 'domiciliar' | `23514` | REJEITADO |
| `ck_evolucoes_humor` | Humor 11 | `23514` | REJEITADO |
| `ck_evolucoes_relato_minimo` | Relato com 5 caracteres | `23514` | REJEITADO |
| `ck_psicologos_valor_positivo` | valor_sessao = 0 | `23514` | REJEITADO |

### 4.1 Mensagens retornadas pelo PostgreSQL

**ck_pacientes_cpf_formato** - CPF com letras

```text
ERROR:  new row for relation "pacientes" violates check constraint "ck_pacientes_cpf_formato"
```

**ck_pacientes_nascimento** - Data de nascimento futura

```text
ERROR:  new row for relation "pacientes" violates check constraint "ck_pacientes_nascimento"
```

**ck_pacientes_genero** - Genero fora do dominio

```text
ERROR:  new row for relation "pacientes" violates check constraint "ck_pacientes_genero"
```

**ck_consultas_duracao** - Duracao de 10 minutos

```text
ERROR:  new row for relation "consultas" violates check constraint "ck_consultas_duracao"
```

**ck_consultas_modalidade** - Modalidade 'domiciliar'

```text
ERROR:  new row for relation "consultas" violates check constraint "ck_consultas_modalidade"
```

**ck_evolucoes_humor** - Humor 11

```text
ERROR:  new row for relation "evolucoes" violates check constraint "ck_evolucoes_humor"
```

**ck_evolucoes_relato_minimo** - Relato com 5 caracteres

```text
ERROR:  new row for relation "evolucoes" violates check constraint "ck_evolucoes_relato_minimo"
```

**ck_psicologos_valor_positivo** - valor_sessao = 0

```text
ERROR:  new row for relation "psicologos" violates check constraint "ck_psicologos_valor_positivo"
```

## 5. Conclusao

- 22 de 22 testes HTTP retornaram o status esperado.
- 8 de 8 CHECK constraints rejeitaram corretamente os dados invalidos.
- As stored procedures aplicaram as regras de negocio (CPF/e-mail unicos, idade minima, conflito de agenda e evolucao unica).
- As views com JOIN e as funcoes de relatorio responderam com dados consistentes.
- O script `pytest` complementa esta evidencia com 55 testes automatizados (unitarios, de API e de integridade do banco).

---

Evidencia em JSON: `docs/testes/resultado_testes.json`.
