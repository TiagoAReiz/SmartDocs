# Design: delete-document

## Context
Currently, the system allows uploading and processing documents, but it lacks a feature to permanently delete a document. A document consists of its main record in the `documents` table, associated extracted fields (`document_fields`), tables (`document_tables`), chunked data for RAG (`document_chunks`), processing logs (`document_logs`), and related contracts (`contracts`). Further, the original uploaded file resides in Azure Blob Storage.

## Goals / Non-Goals
**Goals:**
- Implement a hard-delete endpoint `DELETE /admin/documents/{document_id}` for documents.
- Ensure all associated relational data (fields, tables, chunks, logs, contracts) are deleted when a document is deleted.
- Remove the physical file from Azure Blob Storage.
- Provide UI in the frontend `AdminDocumentsPage` for triggering the deletion with a confirmation dialog.

**Non-Goals:**
- Soft deletion (marking as deleted without removing from DB).
- Batch deletion of multiple documents at once (can be added later if needed).

## Decisions
1. **Database Cascade Delete**: The existing `Document` SQLAlchemy model already has `cascade="all, delete-orphan"` configured for its relationships (`fields`, `tables`, `contracts`, `logs`, `chunks`). The database foreign keys (`ondelete="CASCADE"`) are also in place. This means executing `await db.delete(doc)` will automatically clean up the relational data.
2. **Blob Storage Cleanup**: Before or after deleting the record from the database, a call must be made to `storage_service.delete_blob(doc.blob_url)` to avoid orphaned files in Azure Blob Storage.
3. **Audit Logging**: The deletion action must be logged using the `AuditService` to maintain a trail of who deleted the document, similar to other admin actions.

## Risks / Trade-offs
- **Risk**: Deleting a document that is actively being queried or used in an active chat session.
  - **Mitigation**: Once deleted, subsequent queries relying on that document's chunks will simply not find them. Chat history might still reference the document name as text, but links to it will return 404. This is acceptable for a hard delete.
- **Risk**: Storage deletion fails after DB deletion (or vice-versa).
  - **Mitigation**: We should attempt to delete from storage first, or wrap it in a robust error handling block. If storage deletion fails, we can log an error but still proceed with DB deletion, or we can abort the DB deletion. Aborting DB deletion if blob storage deletion fails is safer to prevent data inconsistency.
