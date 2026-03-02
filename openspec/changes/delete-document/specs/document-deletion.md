# specs/document-deletion

## ADDED Requirements

### Requirement: Document Deletion
The system MUST allow administrative users to completely delete a document.

#### Scenario: Successful hard deletion
- **GIVEN** an existing document with ID `doc_123`
- **AND** the document has associated `documents_fields`, `document_tables`, and `document_chunks`
- **WHEN** an admin user requests to delete `doc_123`
- **THEN** the document is removed from the `documents` table
- **AND** all associated `documents_fields` are removed
- **AND** all associated `document_tables` are removed
- **AND** all associated `document_chunks` are removed from the vector database (if applicable) and relational database
- **AND** the API responds with a 204 No Content success status

#### Scenario: Unauthorized deletion attempt
- **GIVEN** an existing document with ID `doc_123`
- **WHEN** a non-admin user requests to delete `doc_123`
- **THEN** the API responds with a 403 Forbidden error
- **AND** the document and its associations remain intact

#### Scenario: Delete button UI visibility
- **GIVEN** a user is on the documents list page
- **WHEN** the user is an admin
- **THEN** the delete action button is visible for documents
- **WHEN** the user is a standard user
- **THEN** the delete action button is hidden
