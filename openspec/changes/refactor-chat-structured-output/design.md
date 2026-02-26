# Design: Refactor Chat Structured Output

## Context
Currently, the `ChatService` in the backend uses a ReAct agent (`create_react_agent` from LangGraph/LangChain) with Azure OpenAI. The agent autonomously decides whether to answer directly or use tools (`database_query`, `rag_search`). The prompt is defined as a large string (`SYSTEM_PROMPT`) inside `chat_service.py`.

The output to the frontend is mostly raw text (sometimes containing markdown tables) and a separate `data` array that captures raw SQL rows via a callback in the tools. However, this structure is brittle:
1. The model doesn't guarantee the format of the explanation.
2. The rules for step-by-step logic (RAG -> SQL on `documents` -> `document_fields` -> `document_tables`) are embedded in the prompt and often ignored or misinterpreted by the LLM.
3. The frontend `ChatPage` just renders `ReactMarkdown` and a `ChatDataTable` based on the raw `msg.data` array, which doesn't know which fields/tables are truly relevant to the answer.

## Goals / Non-Goals

**Goals:**
- Move complex prompts to Azure OpenAI or configure them cleanly via an externalized template system if staying in the code, but adopt the **Structured Outputs** feature of OpenAI (via LangChain's `with_structured_output` or similar Pydantic bound schema) for the final response.
- Enforce the logical steps (RAG first -> Filter -> Data Extraction) via LangGraph workflow or strict tool definition, rather than just prompt pleading.
- Return a strict JSON structure containing:
  - `message`: Friendly text response.
  - `final_query`: The SQL or RAG query description used.
  - `documents`: An array of objects with `id`, `relevant_field_keys`, and `relevant_tables` (with `index`, `row`, `col`, `header`).
- Update the frontend (`chat/page.tsx` and `ChatDataTable`) to map this new rich JSON structure into beautiful UI components.
- Update `ChatResponse` taking into account the new structured payload.

**Non-Goals:**
- Completely replacing LangChain/LangGraph. We will refactor how we use them, not remove them.
- Changing the underlying database schema.
- Creating new OCR extraction pipelines.

## Decisions

### 1. Model Call Architecture (Backend)
**Decision**: Use Pydantic to define the final expected output schema and use OpenAI's `Structured Outputs` feature (e.g., `llm.with_structured_output(ChatFinalResponseSchema)`).
**Rationale**: Pydantic schemas guarantee the exact JSON structure we described in the proposal. It prevents the model from returning raw markdown tables when we actually need structured data arrays for the frontend to render properly.

### 2. Prompt Management
**Decision**: Refactor `SYSTEM_PROMPT` into a cleaner, focused set of instructions. If utilizing Azure OpenAI's portal for prompt management is strictly required by the user, we will create placeholders/variables to fetch it. Otherwise, we will cleanly separate the prompt into a distinct template file/module away from the business logic.
**Rationale**: Keeps `chat_service.py` clean.

### 3. Agent Tool Flow
**Decision**: Allow the ReAct agent to decide between SQL and RAG based on the intent. For questions involving dates, filtering by status, or limiting recent documents (e.g., "últimos 15 documentos enviados" or "documentos de hoje"), the agent may use `database_query` directly. For extracting specific non-metadata content or searching by names/CNPJs that might be hidden inside the text, the agent should prioritize `rag_search`.
**Rationale**: Forcing RAG before SQL for obvious database queries like "documentos de hoje" is inefficient and wastes resources. The agent prompt will be updated (or workflow defined) to clarify *when* to prioritize each tool, rather than blindly demanding RAG first.

### 4. Frontend Payload Parsing
**Decision**: Update `ChatResponse` model in `schemas/chat.py` to match the new structure. Update `useChat.ts` to parse `msg.documents` and `msg.message`. The `ChatDataTable` component will be adapted to handle the nested `relevant_field_keys` and `relevant_tables`.
**Rationale**: The frontend needs to be aware of the new structure to render the unique data tables per document, rather than one huge generic data grid.

## Risks / Trade-offs

- **Risk**: LangChain's ReAct agent + `with_structured_output` can sometimes be tricky to combine, as the ReAct agent expects to output a specific action/observation sequence.
- **Mitigation**: We may need to separate the "Reasoning/Tool Use" phase from the "Final Answer Generation" phase. Phase 1: ReAct agent gathers data. Phase 2: A separate LLM call with `with_structured_output` synthesizes the gathered data into the strict JSON format.
- **Trade-off**: Two LLM calls (Reasoning + Synthesis) increase latency and token usage but guarantee output structure and reliability.

## Implementation Plan (High Level)
1. **Schema Definition**: Define `StructuredChatResponse` in `schemas/chat.py`.
2. **Phase 2 LLM Call**: In `chat_service.py`, after the ReAct agent finishes gathering information (or stream of information), pass the trajectory/messages to a final LLM chain bound to the Pydantic schema to generate the strict JSON.
3. **Frontend Types**: Update `types/chat.ts` to include the new structures.
4. **Frontend UI**: Update `chat/page.tsx` and `components/chat-data-table.tsx` to handle the `documents` array structure.
