n# Proposal: Add Audit System

## Motivation
<!-- Explain the motivation for this change. What problem does this solve? Why now? -->
Um sistema de auditoria (audit log) é fundamental para governança, segurança e rastreabilidade no app. Precisamos mapear as ações que alteraram, criaram ou deletaram os registros (como documentos, chats e contratos) especificando qual usuário as realizou, através de uma nova arquitetura de tabelas. Além disso, precisamos dar visibilidade e recursos de filtros de pesquisa aos administradores.

## Proposed Changes
<!-- Describe what will change. Be specific about new capabilities, modifications, or removals. -->
1.  **Mapeamento de Ações**: Rastrear logs de alteração, criação e deleção (CREATE, UPDATE, DELETE) em entidades (Usuários, Documentos/Contratos e Chats). Evitaremos mapear mensagens do chat individuais para não poluir o banco e onerar o logging.
2.  **Tabela de AuditLog**: Criação de model `AuditLog` no PostgreSQL com colunas: usuário, email (snapshot do login atual do autor da ação para não perder o log caso o usuário seja apagado), ID da entidade alvo, tipo da entidade, tipo de ação, objeto JSON `old_values` e JSON `new_values`, data da ação (`created_at`).
3.  **Endpoint API Admin**: Rota `/api/admin/audit-logs` exclusiva para requisições de Admin, dispondo de paginação, filtros estruturados (por e-mail, tipo de ação e entidade alvo), além de ordenações baseadas na data de ação (temporal padrão desc) ou por e-mail do autor (alfabética).
4.  **Interface Frontend Admin**: UI Web totalmente privada para os administradores visualizarem os `AuditLogs` numa `DataTable` avançada contendo busca simplificada e filtros em colunas-chave, além de expansão de linha para os campos `new_values` e `old_values`.

## Capabilities
### New Capabilities
<!-- What new spec-level capabilities will be created? Each creates specs/<name>/spec.md -->
- `audit-logging`: Camada de back-end foca em prover endpoints de Admin e a tabela AuditLog com serviço de captura (intercepção) de CRUD, salvando payloads e identificando usuários que agiram.
- `admin-audit-dashboard`: Tela (view) administrativa no Frontend que agrupa DataTable paginado e filtrado de auditoria.

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing -->
<!-- (none yet, as we are creating an auditing layer spanning across them) -->

## Impact
<!-- Affected code, APIs, dependencies, systems -->
- **Database**: Nova tabela no PostgreSQL (`audit_logs`) desenhada para escalar muito em volume de linhas armazenadas.
- **API (Backend)**: Teremos que criar router de administração (`admin_router`), middleware local ou wrappers na camada de serviço (ex. injetar `audit_logger.log_action()`) junto com o background tasks do FastAPI para não penalizar o TTFB (Time To First Byte) das respostas do cliente durante a gravação extra no banco.
- **Frontend App**: Ponto cego de segurança com permissões resolvido. A UI necessitará de rotas guardadas pelo hook de claims Admin. O componente de tabela usará a estrutura de DataTable presente baseada em TanStack Table / Shadcn.
