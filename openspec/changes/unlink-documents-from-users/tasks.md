# Unlink Documents from Users - Implementation Tasks

## 1. Database & Models
- [x] 1.1 Update `app/models/document.py`: Remove `user_id` column and `user` relationship.
- [x] 1.2 Update `app/models/user.py`: Remove `documents` relationship.
- [x] 1.3 Generate Alembic migration: Run `alembic revision --autogenerate -m "unlink documents from users"` and verify the script drops the `user_id` column from `documents`.
- [x] 1.4 Apply Alembic migration to local database.

## 2. Backend API
- [x] 2.1 Update `app/api/documents.py` (List API): Remove `user_id` filtering from `select(Document)`.
- [x] 2.2 Update `app/api/documents.py` (Upload API): Remove `user_id` assignment when creating a `Document`.
- [x] 2.3 Update `app/api/documents.py` (Get/Delete/Process APIs): Remove any authorization checks that require the document to belong to `current_user`.
- [x] 2.4 Update Audit Logging (Upload API): Ensure the `CREATE` action in `AuditService` logs the user performing the upload, even though the document record doesn't store it.

## 3. Frontend Integration
- [x] 3.1 Update `frontend/src/services/documentService.ts`: Inspect and remove any payload/query parameters sending `user_id` for document actions (if applicable).
- [x] 3.2 Update Document Listing UI: Verify there is no "My Documents" vs "All Documents" distinction in the frontend components, and adjust wording if necessary to reflect global documents.

## 4. Verification & Testing
- [x] 4.1 Run backend tests and fix any failing tests related to user-document ownership.
- [x] 4.2 Manually test document upload: Verify it uploads successfully and the `AuditLog` captures the uploader.
- [x] 4.3 Manually test document listing: Verify a newly created user can immediately see documents uploaded by other users.
- [x] 4.4 Manually test user deletion: Verify deleting a user successfully completes without foreign key errors and leaves their documents intact.
