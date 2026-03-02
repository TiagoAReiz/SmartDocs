# global-documents

## Overview

Documents are global entities within the system. They are not owned by, linked to, or restricted by individual users. Any user with appropriate system access (such as an Admin) can view, manage, and delete any document, and the deletion of a user will not affect existing documents.

## Requirements

### Requirement: Documents have no user owner
- **GIVEN** a document is uploaded to the system
- **WHEN** the document is saved in the database
- **THEN** it must not have a required `user_id` association

### Requirement: User deletion does not delete documents
- **GIVEN** a user account exists and has previously uploaded documents
- **WHEN** the user account is deleted
- **THEN** all documents previously uploaded by that user must remain intact in the system

### Requirement: Global Document Listing
- **GIVEN** an admin or authorized user requests the list of documents
- **WHEN** the API returns the list
- **THEN** it must include all documents in the system, regardless of who originally uploaded them
