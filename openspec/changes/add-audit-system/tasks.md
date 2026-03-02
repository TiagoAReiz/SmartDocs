# Implementation Tasks: Audit System

## 1. Backend: Banco de Dados e Models
- [x] 1.1 Criar o model `AuditLog` no SQLAlchemy (`app/models/audit_log.py`) com os atributos definidos no design (user_id FK, user_email, entity_type, entity_id, action_type ENUM, old_values, new_values, ip_address, created_at).
- [x] 1.2 Atualizar init dos models (`app/models/__init__.py`) para que o Alembic enxergue o novo model.
- [x] 1.3 Gerar e aplicar a migração baseada no Alembic (`alembic revision --autogenerate -m "Add audit log model"` e `alembic upgrade head`).

## 2. Backend: Service de Gravação
- [x] 2.1 Criar `app/services/audit_service.py` com a classe `AuditService`.
- [x] 2.2 Implementar o método `log_action` (que receberá de input o usuário atual, entity, type, e os diffs em formato de dict/json) assíncrono para abstrair via `BackgroundTasks` ou threadpool.

## 3. Backend: Instrumentar Actions Existentes
- [x] 3.1 Identificar e injetar a gravação de auditoria em ações de Users (Criar/Deletar via Admin ou self-registration).
- [x] 3.2 Identificar e injetar a gravação de auditoria em ações de Documents e Contracts (Upload, Renomeação, Deleção).
- [x] 3.3 Identificar e injetar a gravação de auditoria em ChatThreads (O endpoint que cria um thread e o que deleta).

## 4. Backend: API Admin Dashboard
- [x] 4.1 Modificar as dependências para garantir um `get_current_admin_user` em `app/api/deps.py` (ou onde ficar essa validação de role).
- [x] 4.2 Criar o router `app/api/admin_audit.py` e o Endpoint `GET /api/admin/audit-logs`.
- [x] 4.3 Implementar paginação, ordenação (`sort_by`, `order`) e filtragem (`action_type`, `user_email`) no SQLAlchemy (Async). Inserir no `main.py`.
- [x] 4.4 Incluir esse roteador no `app/main.py`.

## 5. Frontend: Preparação do Admin
- [x] 5.1 Garantir que exista uma rota segura React (protected route) mapeada para `/admin/audit` acessível apenas para perfis Admin.
- [x] 5.2 Criar componentes para visualização (`AuditLogsPagina`):
  - [x] 5.3 Tabela de dados (colunas: `Data`, `Usuário`, `Ação`, `Entidade`, `Detalhes`).
  - [x] 5.4 Filtros superiores (Input Email, Select Ação, Select EntityType).
- [x] 5.5 Gerar o type/interface Typescript (`AuditLog`, `PaginatedAuditLogs`, etc.) no front que espelha as respostas da API Backend.
- [x] 5.6 Criar hook customizado `useAuditLogs` usando o React Query ou `fetch` normal com suporte ao params de URL e cache se apropriado.

## 6. Frontend: Construção do Componente do Dashboard
- [x] 6.1 Implementar a página Base de Auditoria em `pages/Admin/AuditLogs.tsx`.
- [x] 6.2 Adicionar os componentes visuais para os filtros (Input para busca por email, Selects para Type de Action e Entity). Ligar aos states e trigger de busca.
- [x] 6.3 Instanciar a Tabela de Dados contendo as colunas de "Data", "E-mail Autor", "Entidade", "Ação" e um botão/ícone de "Ver Detalhe".
- [x] 6.4 Implementar uma expansão de linha, Modal ou Drawer que renderize o `old_values` (esquerda/cima) e o `new_values` (direita/baixo) na interface quando for acionado o "Ver Detalhe".
