# Unlink Documents from Users - Technical Design

## Architecture Context

Currently, the `Document` model acts as a child of the `User` model. All queries related to listing or interacting with documents inherently require a user context. The new design shifts `Document` to a top-level global entity, independent of user ownership. 

## Implementation Details

### Database Schema Changes

We will rely on SQLAlchemy and Alembic.
1. **Model Update `app/models/document.py`**:
   - Remove the `user_id` column: `user_id: Mapped[int] = mapped_column(...)`
   - Remove the `user` relationship: `user = relationship("User", back_populates="documents")`
2. **Model Update `app/models/user.py`**:
   - Remove the `documents` relationship: `documents = relationship("Document", back_populates="user", ...)`
3. **Migration**:
   - Generate an Alembic migration script to `ALTER TABLE documents DROP COLUMN user_id;`.

### Backend API Changes

1. **`app/api/documents.py`**:
   - **Upload (`POST /documents/upload`)**: Remove the assignment of `user_id` to the newly created document. The endpoint may still require authentication (e.g., to ensure only registered users upload), but the ownership is not recorded via `user_id`. (We need to confirm if we log the uploader elsewhere, e.g. Audit Logs, but not in the `documents` table).
   - **List (`GET /documents`)**: Modify the `select(Document).where(Document.user_id == current_user.id)` query to simply `select(Document)`, removing the `user_id` filter completely.
   - **Get/Delete/Process Endpoints**: Remove any validation that checks if `document.user_id == current_user.id`.

### Frontend Changes

1. **`frontend/src/services/documentService.ts`**:
   - If there are any explicit references or filters passing `user_id` to the backend, they should be removed. Since the backend signature will remain largely the same for listing (just returning more items), minimal frontend service changes are expected.
2. **Components**:
   - The document listing views will now display all documents in the system. Verify that there's no UI element explicitly rendering "My Documents" versus "All Documents" if all are now global.

## Risks / Trade-offs

- **Security/Privacy**: All authenticated users with access to the document list will see *all* documents. If the system previously relied on this for data isolation between users, this isolation is now completely removed. The assumption is that this system acts as a shared, global knowledge base, so this is the intended behavior.
- **Auditability**: By removing `user_id` from the `documents` table, it becomes harder to trace who originally uploaded a specific document unless this information is captured separately in the `audit_logs` table at creation time. The `AuditService` should log the `CREATE` action with the uploader's context.
