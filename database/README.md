# Banco de dados - Mente Saudavel

Os scripts foram escritos para **PostgreSQL 14+** e devem ser executados nesta ordem:

| Ordem | Arquivo | Conteudo |
|-------|---------|----------|
| 0 | `00_create_database.sql` | Cria o banco `mente_saudavel` (executar conectado ao banco `postgres`) |
| 1 | `01_schema.sql` | Tabelas, PKs, FKs, check constraints, indices, triggers e auditoria |
| 2 | `02_views.sql` | Views com JOIN e funcoes de consulta/relatorio |
| 3 | `03_procedures.sql` | Stored procedures (incluindo o relatorio com refcursor) |
| 4 | `04_seed.sql` | Dados de exemplo |

## Execucao via psql

```bash
psql -U postgres -f database/00_create_database.sql
psql -U postgres -d mente_saudavel -f database/01_schema.sql
psql -U postgres -d mente_saudavel -f database/02_views.sql
psql -U postgres -d mente_saudavel -f database/03_procedures.sql
psql -U postgres -d mente_saudavel -f database/04_seed.sql
```

## Testando a procedure de relatorio (refcursor)

```sql
BEGIN;
CALL sp_relatorio_atendimentos(CURRENT_DATE - 30, CURRENT_DATE, 'relatorio');
FETCH ALL FROM relatorio;
COMMIT;
```

## Regras de integridade implementadas

- **PKs**: todas as tabelas possuem chave primaria (`SERIAL`).
- **FKs**: `consultas` referencia `pacientes` e `psicologos`; `evolucoes` referencia `consultas`.
- **Check constraints** (mais de 20 no total), entre elas:
  - `ck_pacientes_cpf_formato` - CPF com exatamente 11 digitos;
  - `ck_pacientes_nascimento` - data de nascimento valida (nao futura);
  - `ck_pacientes_status` - apenas `ativo` ou `inativo`;
  - `ck_consultas_duracao` - entre 15 e 180 minutos;
  - `ck_consultas_modalidade` - `presencial` ou `online`;
  - `ck_evolucoes_humor` - nota de 1 a 10;
  - `ck_evolucoes_relato_minimo` - relato com pelo menos 10 caracteres.
- **Unicidade**: CPF, e-mail e CRP unicos; uma evolucao por consulta.
- **Agenda**: indice unico parcial impede dois agendamentos ativos no mesmo
  horario para o mesmo psicologo (consultas canceladas liberam o horario).
- **Auditoria**: trigger registra INSERT/UPDATE/DELETE de pacientes em
  `auditoria_pacientes` com snapshots em JSONB.
