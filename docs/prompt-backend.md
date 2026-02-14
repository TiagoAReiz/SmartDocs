# Prompt — Implementação do Backend (FastAPI)

---

Preciso que você implemente o backend completo do **SmartDocs**, um sistema de gestão de documentos inteligente com chat SQL, usando **Python + FastAPI**.

## Contexto

O sistema aceita upload de documentos (PDF, DOCX, XLSX, PPTX, JPG, PNG), extrai dados via Azure AI Document Intelligence, armazena tudo no PostgreSQL em 3 camadas (bruta, extraída, normalizada) e possui um chat onde o usuário pergunta em linguagem natural, a IA gera SQL com guardrails, executa no banco e responde.

## Documentos de referência no projeto

- **`docs/arquitetura-backend.md`** — Stack completa de libs, estrutura de pastas, fluxos (upload e chat SQL), decisões de arquitetura, `requirements.txt` e `docker-compose.yml`
- **`docs/rotas-backend.md`** — 13 endpoints com request/response JSON detalhados, mapeados para cada tela do frontend

Siga esses documentos como spec. Eles são a fonte de verdade.

## O que implementar

### 1. Setup do projeto
- Criar a estrutura de pastas conforme `docs/arquitetura-backend.md`
- `requirements.txt` com todas as libs listadas
- `docker-compose.yml` com PostgreSQL 17 + app
- `Dockerfile` com Python 3.12 + LibreOffice headless
- `.env.example` com todas as variáveis necessárias
- `alembic init` configurado para async

### 2. Database (SQLAlchemy + Alembic)
- Models em `app/models/`: User, Document, DocumentField, DocumentTable, Contract, DocumentLog
- `app/database.py` com `create_async_engine` + `AsyncSession` + dependency `get_db`
- Migration inicial com Alembic gerando todas as tabelas do DDL

### 3. Auth (JWT + Argon2)
- `app/core/security.py`: criar/verificar JWT com PyJWT, hash de senha com pwdlib/Argon2
- `app/core/deps.py`: dependencies `get_current_user` e `require_admin`
- Endpoints `POST /auth/login` e `GET /auth/me` conforme `docs/rotas-backend.md`

### 4. Documents
- `POST /documents/upload` — recebe multipart, salva no Blob (ou filesystem no MVP), cria registro no banco, dispara `BackgroundTask` para processamento
- `POST /documents/{id}/reprocess` — reseta status e reprocessa
- `GET /documents` — listagem paginada com filtros (search, status)
- `GET /documents/{id}` — detalhes completos com fields e tables
- `GET /documents/{id}/file` — retorna/redireciona para o arquivo original

### 5. Services
- `conversion_service.py` — DOCX/PPTX/XLSX → PDF via LibreOffice headless (`subprocess`)
- `extraction_service.py` — Azure Document Intelligence: enviar PDF, parsear `raw_json`, extrair fields e tables
- `document_service.py` — orquestra upload → conversão → extração → salvar no banco → atualizar status
- `sql_guard.py` — validar SQL gerado: só SELECT, injetar LIMIT 100, filtrar por user_id para não-admins (usar `sqlparse`)

### 6. Chat (NL → SQL → Resposta)
- `chat_service.py` — recebe pergunta, monta prompt com schema do banco, chama Azure OpenAI, valida SQL com sql_guard, executa query, manda resultado pro modelo formular resposta em PT-BR
- `POST /chat` conforme `docs/rotas-backend.md`
- `GET /chat/history` — histórico de mensagens do usuário

### 7. Admin
- CRUD de usuários (`GET`, `POST`, `PUT`, `DELETE /admin/users`) conforme `docs/rotas-backend.md`
- Apenas usuários com `role=admin` acessam essas rotas

### 8. Config e Error Handling
- `app/config.py` com `pydantic-settings` carregando `.env`
- `app/core/exceptions.py` com exception handlers customizados (404, 401, 403, 409, 500)
- Logging com `loguru`

## Regras importantes

- **Async em tudo**: todas as queries no banco devem usar `AsyncSession`
- **Validação com Pydantic v2**: schemas separados dos models (pasta `schemas/`)
- **Segurança**: nunca expor `password_hash`, sempre filtrar por `user_id` nas queries de documentos
- **Não usar `passlib`**: usar `pwdlib[argon2]` conforme recomendação atual do FastAPI
- **SQL Guardrails são obrigatórios**: o chat NUNCA deve executar DELETE, UPDATE, INSERT, DROP
- **ORJSONResponse** como response class padrão do FastAPI

## Resultado esperado

O backend deve subir com `docker-compose up`, rodar migrations com `alembic upgrade head`, e todos os 13 endpoints devem funcionar conforme os payloads documentados em `docs/rotas-backend.md`.
