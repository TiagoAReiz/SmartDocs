# Implementation Tasks: async-doc-processing

## Phase 1: Database & Models (Backend)
- [x] Criar migração no Alembic e adicionar a tabela `document_processing_jobs` (id, document_id, status, error_log, attempts, timestamps) no banco PostgreSQL.
- [x] Criar o model SQLAlchemy correspondente em `backend/app/models/document_processing_job.py`.
- [x] Adicionar os Schemas Pydantic (Create, Read, Update) relacionados em `backend/app/schemas/`.

## Phase 2: Core Processing Worker (Backend)
- [x] Criar módulo `backend/app/services/worker_service.py` contendo a lógica central do worker.
- [x] Implementar a query de fila segura: `SELECT ... FOR UPDATE SKIP LOCKED` para buscar um `PENDING` job.
- [x] Mover a lógica atual de chamada síncrona do Azure Document Intelligence do `document_service.py` para dentro da função execute do worker.
- [x] Atualizar o status do job (PROCESSING -> COMPLETED/FAILED) ao redor da lógica da Azure.
- [x] Integrar a rotina de retry no caso de exception (adicionando log ao `error_log` e incrementando `attempts`).

## Phase 3: API & Endpoint Adaptation (Backend)
- [x] Refatorar o `POST /documents` (função `process_document_transaction` no `document_service.py`) para **não** chamar o Azure. Ele deve apenas salvar no DB, criar o Job como `PENDING`, gerar o Blob e retornar o documento criado pra UI imediatamente.
- [x] Criar a nova rota `GET /documents/{document_id}/status` no `document_router.py` que consulta a tabela `document_processing_jobs` e retorna o status atual.

## Phase 4: Container & Orchestration (Infra)
- [x] Criar o script de entrypoint para o worker (ex: `backend/worker_main.py`) que inicializa um loop infinito assíncrono buscando jobs a cada `N` segundos.
- [x] Atualizar o `docker-compose.yml` para rodar este `worker_main.py` como um container/serviço separado do servidor uvicorn principal, garantindo isolamento de CPU.

## Phase 5: Client / Frontend Polling
- [x] Atualizar as tipsagens Typescript e chamadas API (`api.ts` ou hooks de query/swr) para lidar com a nova rota de status.
- [x] No componente da Tabela de Documentos (`DocumentsTable.tsx`), identificar documentos recém adicionados cujo status esteja pendente.
- [x] Implementar SWR polling condicional na linha da tabela. Exemplo: `useSWR(doc.id + '/status', fetcher, { refreshInterval: isPending ? 3000 : 0 })`.
- [x] Atualizar visualização do frontend (Loader rotatório da coluna Status no lugar do Check quando Pendente, e erro vermelho quando Falha).
