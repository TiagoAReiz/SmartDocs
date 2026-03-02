# Design: Audit System

## Context
<!-- Background and current state -->
Atualmente, o app SmartDocs realiza operações vitais como upload de documentos, extrações de dados e sessões de chat sem um registro centralizado acessível por administradores que detalhe *quem* realizou cada ação, *quando* e *quais dados* exatos foram alterados. Esse vácuo de observabilidade prejudica a governança e dificulta a auditoria de modificações em entidades sensíveis.

## Goals / Non-Goals

**Goals:**
<!-- What this design will achieve -->
*   Garantir a persistência imutável de um Audit Log abrangendo ações do tipo CREATE, UPDATE, DELETE e PROCESS.
*   Registrar adequadamente o ID do usuário autor da ação e um snapshot de seu e-mail para preservação histórica, mesmo que o usuário seja removido.
*   Armazenar um diff ou snapshot dos dados envolvidos (JSONB contendo `old_values` e `new_values`).
*   Prover endpoint administrativo robusto com paginação, filtragem (por e-mail, entidade e ação) e ordenações.

**Non-Goals:**
<!-- What is explicitly out of scope -->
*   Restaurar dados diretamente a partir do log de auditoria (rollback automatizado). Servirá apenas para consulta.
*   Registrar eventos granulares de mensagens no chat individuais (`chat_message` não será logado, apenas `chat_thread` iniciais e exclusões).
*   Monitoramento de performance do banco de dados atrelado à tabela de log.

## Proposed Architecture
<!-- High-level architecture and components -->
1.  **Database Layer (PostgreSQL / SQLAlchemy)**: 
    *   Nova tabela `audit_logs` mapeada em `app/models/audit_log.py`.
    *   Uso do tipo JSONB para os campos `old_values` e `new_values` para máxima flexibilidade aos schemas distintos (Users, Documents, Contracts).
    *   Indexação no `user_email`, `entity_type`, `action_type` e `created_at` para acelerar os filtros do dashboard Admin.

2.  **Service Layer (FastAPI)**:
    *   Criação de um novo serviço `AuditService` (`app/services/audit_service.py`) com um método principal assíncrono `log_action()`.
    *   Isso será chamado de forma explícita após cada transação de sucesso pelas rotas ou background tasks (ex: na camada de controller de Documentos ou na função que processa extração de OCI PDF).
    *   **Injeção de BackgroundTasks**: Para não segurar o response do usuário, o `log_action` do Service agendará as escritas no banco no loop de background do FastAPI usando `BackgroundTasks`.

3.  **API Endpoints**:
    *   Novo roteador: `app/api/admin_audit.py`.
    *   Dependência (Dependency Injection) verificando se a rule do usuário JWT é Admin (ex: `get_current_admin_user`).
    *   Endpoint `GET /api/admin/audit-logs` aceitando queries paramétricas.

4.  **Frontend Admin Dashboard**:
    *   O route `/admin/audit` receberá um componente (ex: `pages/Admin/AuditLogs.tsx`).
    *   Utilizará `tanstack/react-table` ou o componente padronizado do Shadcn UI com `DataTable` renderizando os registros retornados.

## Data Model / Schema Changes
<!-- Database schema, API requests/responses, state structures -->
```python
# app/models/audit_log.py
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import enum
from .base import Base

class ActionType(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    PROCESS = "PROCESS"

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email = Column(String, index=True, nullable=False)
    
    entity_type = Column(String, index=True, nullable=False) # Ex: "DOCUMENT", "USER", "CONTRACT"
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    
    action_type = Column(SQLEnum(ActionType), nullable=False, index=True)
    
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    ip_address = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
```

**API Request / Response** (`GET /api/admin/audit-logs`):
```typescript
// Query params interface
interface AuditLogQuery {
  page: number; // default 1
  limit: number; // default 50
  email?: string;
  action_type?: string; // enum
  entity_type?: string; 
  sort_by?: 'created_at' | 'user_email'; // default created_at
  sort_order?: 'asc' | 'desc'; // default desc
}

// Response interface
interface PaginatedAuditLogs {
  data: AuditLogItem[];
  total: number;
  page: number;
  limit: number;
}
```

## Risks / Trade-offs
<!-- Known risks and trade-offs -->
*   **Performance vs Exaustividade**: Gravar cada ação consome tempo e recursos do banco (`INSERT` extra + parse JSONB). **Mitigação**: O uso de `BackgroundTasks` do FastAPI aliviará a latência da requisição síncrona, e estamos excluindo deliberadamente o chat (`chat_message`) dessa auditoria.
*   **Crescimento de Disco a Longo Prazo**: A tabela `audit_logs` será a que mais crescerá. Se o volume se tornar crítico (>10M linhas rápidas), estudaremos uma regra de arquivamento (cold storage) ou rotatividade (log rotation) futura, mas por enquanto o Postgres suportará perfeitamente.
*   **Concorrência de Estados**: No método explícito (via background task e service code injection), caso o model do BD mude internamente sem passar pelo controller/service primário (ex: um script cron manual), ele passará despercebido da auditoria, exigindo disciplina de código de sempre usar o Service.
