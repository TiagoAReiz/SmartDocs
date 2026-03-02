# Specification: Audit Logging

## OVERVIEW
O backend SmartDocs deve suportar a interceptação e gravação em banco de dados das principais ações de mutação de estado feitas pelos usuários.

## ADDED Requirements

### Requirement: audit-log-creation
Ao realizar operações sensíveis de CREATE, UPDATE ou DELETE nos modelos principais, o sistema deve gravar um registro na tabela de `audit_logs` contendo quem é o usuário autor, seu e-mail de snapshot, o ID do objeto modificado e o diff dos dados (`old_values` e `new_values`).

### Requirement: non-blocking-auditing
A gravação destes logs de auditoria não deve atrasar o tempo de resposta da API para o cliente, utilizando abstrações assíncronas (ex: FastAPI BackgroundTasks).

### Requirement: entity-coverage
As entidades iniciais cobertas devem ser:
- `USER`
- `DOCUMENT`
- `CONTRACT`
- `CHAT_THREAD` (apenas criação da sessão de chat e deleção lógica/física; pulando as mensagens individuais).

## SCENARIOS

### Scenario: Changing an existing Document title
- **WHEN** um usuário altera o título de um documento via API (`UPDATE`)
- **THEN** o `AuditService` deve gravar um log com `action_type = UPDATE`, `entity_type = DOCUMENT`, inserindo o título antigo em `old_values` e o novo em `new_values`.

### Scenario: Deleting a User Account
- **WHEN** um administrador exclui um usuário no app (`DELETE`)
- **THEN** o `AuditService` grava um log indicando quem realizou e os dados excluídos em `old_values`.

### Scenario: Preserving log after user deletion
- **WHEN** um usuário que realizou diversas ações no passado é excluído de vez do banco de dados
- **THEN** a sua chave externa nas tabelas de `audit_logs` deve ir para null (`SET NULL`), mas o `user_email` estático salvo no log deve ser preservado para manter o rastreio.
