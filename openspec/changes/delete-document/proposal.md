# Proposal: delete-document

## Objective
The objective is to allow users to completely delete a document from the system. This involves removing the document itself and all its associated nested data to maintain database integrity and clean up storage. This is a crucial feature for the global documents system, giving administrators control over the knowledge base.

## New Capabilities
- `document-deletion`: The ability to delete a document and cascade this deletion to all related records (`documents_fields`, `document_tables`, `document_chunks`).

## Impacted Capabilities
- `document-management`: Extends current document management by adding the deletion flow and exposing it in the frontend UI.

## Scope Boundary
- Only administrators should be able to trigger document deletion.
- Soft deletes are NOT in scope for this change; we are implementing a hard delete.
- Deletion will cascade automatically via the backend service; no partial deletions are supported.
