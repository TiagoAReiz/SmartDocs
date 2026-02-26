# Specification: dynamic-frontend-tables

## Overview
This specification details how the frontend chat UI will consume the new structured JSON response to render dynamic, document-specific tables and data visualizations.

## Added Requirements

### Requirement: Parse Structured Response
The frontend must correctly type and parse the incoming JSON payload from the backend.
#### Scenario: Receiving a structured message
- **WHEN** the frontend receives a successful chat response
- **THEN** it must map the `message` to the text content, and the `documents` array to the UI state for rendering.

### Requirement: Render Document-Specific Tables
The frontend must display data tables scoped to individual documents, rather than a single generic data grid.
#### Scenario: Rendering relevant fields and tables
- **WHEN** a chat message contains a `documents` array with `relevant_field_keys` or `relevant_tables`
- **THEN** the UI must render a distinct visual block or table for each document, showing only the fields and table rows specified in the payload.

### Requirement: Interactive Data Export
Users must be able to export the structured data presented in the chat UI.
#### Scenario: Exporting document data
- **WHEN** the user clicks the "Export" button on a document's data table
- **THEN** the frontend must generate and download a CSV file containing the specific `relevant_field_keys` and `relevant_tables` shown in the UI.

## Removed Requirements
- The generic `ChatDataTable` component that renders the entire raw `msg.data` array unconditionally is removed or significantly refactored.
