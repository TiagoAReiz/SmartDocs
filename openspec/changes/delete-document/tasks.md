# Tasks: delete-document

## 1. Backend Implementation
- [ ] 1.1 Add `delete_blob` method to `storage_service.py` to handle Azure Blob Storage cleanup.
- [ ] 1.2 Add `DELETE /admin/documents/{document_id}` endpoint in `api/documents.py`.
- [ ] 1.3 Ensure the endpoint uses `storage_service.delete_blob` to remove the physical file.
- [ ] 1.4 Ensure the endpoint uses `await db.delete(doc)` and `await db.commit()` to execute the cascading delete in the database.
- [ ] 1.5 Add `AuditService.log_action` to log the deletion event.

## 2. Frontend Implementation
- [ ] 2.1 Update `src/services/documentService.ts` to include a `deleteDocument` API call.
- [ ] 2.2 Update `src/hooks/useAdminDocuments.ts` (or similar hook) to handle local state deletion and expose `handleDelete`.
- [ ] 2.3 Add a generic "Delete" button to the actions column in `src/app/(app)/admin/documents/page.tsx`.
- [ ] 2.4 Create a confirmation dialog (Alert Dialog) in the UI before executing the backend deletion.

## 3. Testing & Verification
- [ ] 3.1 Verify manual document upload and subsequent hard deletion from the UI.
- [ ] 3.2 Verify that the database deletes cascade properly (`documents_fields`, `document_tables`, `document_chunks` are gone).
- [ ] 3.3 Verify that the file is actually removed from Azure Blob Storage.
