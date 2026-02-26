# Specification: structured-chat-response

## Overview
This specification details the requirement for the backend chat agent to return a strictly structured JSON response using Azure OpenAI, replacing the previous unstructured text output.

## Added Requirements

### Requirement: Structured Output JSON Schema
The backend MUST guarantee that responses from the LangChain/Azure OpenAI agent strictly adhere to a defined JSON schema using the `Structured Outputs` feature.
#### Scenario: Agent responds to user query
- **WHEN** the chat agent finishes processing the user's question (either directly or via tools)
- **THEN** it must output a JSON object containing `message`, `final_query`, and a `documents` array.

### Requirement: Document Data Extraction
The agent must identify which specific fields and tables are relevant to the user's question and include them in the structured output.
#### Scenario: Extracting document values
- **WHEN** the agent retrieves data from `document_fields` or `document_tables`
- **THEN** it must map the internal `document_id` to the `documents` array, including the exact keys in `relevant_field_keys` and the exact coordinates/headers in `relevant_tables`.

### Requirement: Fallback Handling
The system must gracefully handle failures in generating the structured output.
#### Scenario: OpenAI Structured Output fails
- **WHEN** the Azure OpenAI API fails to return the exact JSON structure or times out
- **THEN** the backend must catch the error and return a safe, valid JSON response with a default error `message` and an empty `documents` array, preventing frontend crashes.

## Removed Requirements
- Requirements for the frontend to parse raw markdown tables embedded in text are removed.
- Requirements for the agent to append raw SQL rows to the `data` array as a separate, detached payload are removed.
