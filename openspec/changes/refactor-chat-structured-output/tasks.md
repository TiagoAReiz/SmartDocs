## 1. Backend: Schemas and AI Setup

- [x] 1.1 Update `app/schemas/chat.py` to define the new `StructuredChatResponse` (with `message`, `final_query`, and `documents` list).
- [x] 1.2 Update `ChatResponse` in `schemas/chat.py` to match the exact JSON payload that will be sent to the frontend.
- [x] 1.3 Update `app/services/chat_service.py` `SYSTEM_PROMPT` to clarify the new tool flow (RAG is priority for content, SQL is priority for counting/filtering).

## 2. Backend: Agent Flow Refactor

- [x] 2.1 In `app/services/chat_service.py`, modify `chat` and `chat_stream` logic to use a two-step process: Phase 1 evaluates tools/gathers data via ReAct; Phase 2 uses `with_structured_output` to strictly format the final Pydantic JSON response.
- [x] 2.2 Re-map the `on_data` tool callback to ensure `document_id` and internal references are captured and injected into the final structured LLM call context payload.
- [x] 2.3 Implement error handling for Phase 2 (Structured Output serialization failures) to return a safe fallback JSON response.

## 3. Frontend: Types and Parsing

- [x] 3.1 Update `frontend/src/types/chat.ts` to reflect the new nested JSON structure (add `RelevantField` and `RelevantTable` types inside a `ChatDocument` interface).
- [x] 3.2 Update `frontend/src/hooks/useChat.ts` to correctly parse and store the new `StructuredChatResponse` instead of relying on the old flat `data` array structure.

## 4. Frontend: UI Updates

- [x] 4.1 Refactor `frontend/src/app/(app)/chat/page.tsx` rendering logic to iterate over `msg.documents` instead of `msg.data`.
- [x] 4.2 Update `frontend/src/components/chat-data-table.tsx` to handle scoped tables per document, rendering exact headers/rows and field_keys.
- [x] 4.3 Update the Export CSV functionality in `chat/page.tsx` to seamlessly handle exporting the new nested table format per document.
