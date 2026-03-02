# Problem & Vision

Currently, documents in SmartDocs are linked to specific users via a `user_id` foreign key in the `documents` table. However, the system is designed to be a general knowledge base where documents should be accessible globally, not tied to individual accounts. The current linkage causes issues, such as the need to handle document deletion when an admin or user is removed, which contradicts the system's purpose. This change will unlink documents from users, making them global entities.

# Scope

- Update the `Document` model in `backend/app/models/document.py` to remove the `user_id` column and relationship.
- Create an Alembic migration to apply the schema change (drop `user_id` column).
- Update the `User` model to remove the `documents` relationship.
- Update the backend API (`documents.py`) to remove user filtering when listing, creating, or accessing documents.
- Update backend tests to reflect the unlinked document model.
- Update frontend services (`documentService.ts`) and components to reflect the removal of user-specific document fetching (if applicable).

# New Capabilities

- `global-documents`: Documents are now global and not owned by any specific user.

# Impacted Capabilities

- Document Listing: Will no longer filter by `user_id` or require a user context.
- Document Upload: Wil no longer attach an uploading user.
- User Deletion: Will no longer be blocked by or cascade to documents.

# Technical Impact

- `backend/app/models/document.py`: Remove `user_id` column and user relationship.
- `backend/app/models/user.py`: Remove `documents` relationship.
- `backend/app/api/documents.py`: Remove user dependency from queries.
- `frontend/src/services/documentService.ts`: Remove user-specific logic if present.
- Database: Requires an Alembic migration to drop the `user_id` column.
