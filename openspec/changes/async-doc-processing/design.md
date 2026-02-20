# Design: Processamento Assíncrono de Documentos via Fila no PostgreSQL

## System Architecture

A mudança arquitetural introduz a separação clara entre a requisição de upload HTTP e a extração intensiva de dados (Azure AI), utilizando as ferramentas já presentes na infraestrutura (PostgreSQL + Asyncio Python).

### Componentes Principais

1.  **FastAPI (Main Server):**
    *   Continua lidando com a requisição de upload `POST /documents`.
    *   Faz o upload rápido do blob para o Azure Storage.
    *   Cria o registro principal na tabela `documents` com status transicional.
    *   Cria um registro na tabela `document_processing_jobs`.
    *   Responde "200 Accepted" pro cliente quase instantaneamente.

2.  **Tabela de Fila (PostgreSQL):**
    *   Servirá como nosso Message Broker de baixíssimo overhead.
    *   Estrutura base: tabela `document_processing_jobs` (com campos de relacionalidade pro documento, status local, tentativas e logs de erro).

3.  **Background Worker (Python/Asyncio):**
    *   Um processo independente (podendo rodar no mesmo container do backend com um sub-process gerenciador, ou como um simples container adicional no docker-compose).
    *   Usa polling inteligente e conexões persistentes com a base usando `SELECT ... FOR UPDATE SKIP LOCKED` para puxar *jobs* sem conflito de concorrência.
    *   Executa a chamada síncrona/pesada contra a Azure API.
    *   Processa e salva os chunks/embeddings usando pgvector.
    *   Atualiza as tabelas marcando sucesso ou falha.

4.  **Frontend (Polling):**
    *   A tela interage com o novo endpoint de status `GET /documents/{id}/status`.
    *   Rotinas de polling curtas apenas nos documentos cujo status em tela esteja como "Processando" usando a revalidação focada da React Query ou SWR.

## Data Model

A nova tabela transacional exigirá um schema mapeado em SQLAlchemy:

**Model: `document_processing_jobs`**
*   `id` (UUID, Primary Key)
*   `document_id` (UUID, Foreign Key cascade delete pro respectivo documento)
*   `status` (String/Enum: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`)
*   `created_at` (Timestamp)
*   `started_at` (Timestamp, preenchido quando capturado pelo worker)
*   `completed_at` (Timestamp, preenchido no final)
*   `attempts` (Integer, default 0, para backoffs simples)
*   `error_log` (Text, nullable. Salva a resposta da exception da cloud caso falhe.)

**Tabela: `documents` (Modificada)**
*   Ajuste conceitual: Se um documento já tinha campo de "status" da vector database, talvez ele deva refletir este estado global ou dependamos puramente do estado na tabela de *jobs* para unificar a leitura do front.

## Flow / Sequence

1. **Upload:** User -> POST `/documents` -> FastAPI.
2. **Setup:** FastAPI -> Azure Storage (BLOB).
3. **Queueing:** FastAPI -> INSERT `documents` & `document_processing_jobs` -> HTTP 200 pro User.
4. **Fetching:** Worker -> `SELECT ... FOR UPDATE SKIP LOCKED` -> Marca como `PROCESSING`.
5. **Extraction:** Worker -> Chama Azure Document Intelligence (Wait).
6. **Processing:** Worker -> Divide JSON em chunks, gera embeddings OpenAI -> Salva `document_fields` & `documents` pgvector.
7. **Finalization:** Worker -> Atualiza `document_processing_jobs` pra `COMPLETED`.
8. **UI Update:** Frontend -> Polling `GET /status` -> Recebe `COMPLETED` -> Recarrega Grid.

## Edge Cases

- **Rate Limiting da Azure:** O worker deve ter exceções tratadas de rede, e implementar backoff simples, incrementando as `attempts` no BD se falhar.
- **Worker Crash:** Pode haver registros zumbis (status `PROCESSING` porém travados há muitas horas). Devemos desenhar o Worker para, no seu polling, resgatar jobs com `started_at` expirado ou não criar *commits* no BD até o fim das tarefas. O uso de autocommit desligado do SQLAlchemy é vital durante o `FOR UPDATE`.

## Risks / Trade-offs

*   **Risk:** O uso do PostgreSQL como Message Broker introduz um pequeno padrão de Anti-pattern a depender da escala.
*   **Trade-off:** Assumimos esse risco com conhecimento, devido ao tamanho atual do projeto não justificar o *overhead* e custos de adicionar Redis/Celery/RabbitMQ à infraestrutura ou Azure Serverless Queues. O ganho é entrega extremamente rápida de valor pro usuário final que para de sofrer com travamento do browser em uploads.

*   **Trade-off:** O Polling no Frontend gasta uma fatia pequena de rede da API versus a infraestrutura real-time com Websockets. Websockets seriam "ideais", porém muito intrusivos e de complexa estabilização com FastAPI. O polling de apenas instâncias "PENDING" resolve elegantemente para interfaces do tipo Dashboard.
