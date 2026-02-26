# Proposal: Refactor Chat Structured Output

## Why
Currently, the prompts for our chat agent are messy, scattered throughout the codebase, have poorly defined rules, and follow a flawed step-by-step process. In addition, the current output from the agent is not structured enough to allow the frontend to easily parse and display complex data like tables. We need to implement a newly defined step-by-step process for the agent, centralize the prompts in Azure OpenAI, and utilize OpenAI's Structured Outputs to return a well-defined JSON response. This structured data will include not only the message but also the final query used to get the results and the specific data fields/tables, enabling the frontend to generate rich data visualizations (like tables).

## What Changes
1. **Prompt Centralization & Refactoring**: Move the scattered and messy prompts into Azure OpenAI and redefine them to follow a clear step-by-step logical process.
2. **Step-by-Step Flow Update**:
   - The agent receives the user's question.
   - The agent determines if it can filter documents (in search or RAG) to reduce scope (e.g., ordering by `created_at` and setting a limit).
   - The agent uses the relevant document IDs to fetch relevant data from `document_fields` and `document_tables`.
   - The agent extracts relevant values and returns them in a structured format.
3. **Structured Outputs Implementation**: Implement Azure OpenAI Structured Outputs mechanism in the backend to ensure the model responds with a strictly defined JSON schema.
4. **Backend Output Processing**: Create functions in the backend to parse, structure, and sanitize the agent's output before sending it to the frontend.
5. **Frontend Component Updates**: Modify the chat message component on the frontend to parse the new JSON structure and dynamically render tables and data arrays using the `fields` and `tables` returned by the agent.

## Capabilities
<!-- Capabilities listed here will need a corresponding spec file. Use kebab-case names. -->
- `structured-chat-response`
- `dynamic-frontend-tables`

## Impact
- **Backend API (`chat_service.py`, `tools.py`, `api/chat.py`, `schemas/chat.py`, `models/chat_message.py`)**: Major changes to how the model is called (enabling Structured Outputs), how prompts are constructed, and how the RAG tools are utilized to filter documents before extracting fields and tables.
- **Frontend Components (`chat/page.tsx`, `useChat.ts`, `types/chat.ts`)**: The chat UI message component needs to be updated to handle JSON structures instead of just plain text. New types will be created for the chat message structure, and new rendering logic will be added for data tables.
- **Azure OpenAI Configuration**: Prompts will need to be configured and tested inside the AI platform instead of the backend codebase.
