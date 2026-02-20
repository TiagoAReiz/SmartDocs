# Spec: status-polling

## Scenarios

### Scenario 1: Initial load of documents list

- **GIVEN** a user opens the "Documents" page or views the Data Table
- **WHEN** the frontend fetches the list of documents via the API
- **THEN** it displays all documents, including those with a provisional status (e.g., "Verificando Processamento")
- **AND** the table rows for pending documents show a clear visual indicator (e.g., a spinning loader icon instead of a checkmark)

### Scenario 2: Active polling for document status

- **GIVEN** a document is displayed in the UI with a pending status ("Verificando Processamento")
- **WHEN** the React component mounts or detects this status
- **THEN** it initiates a short-interval polling mechanism (e.g., every 5 seconds using SWR) against the `/documents/{id}/status` endpoint
- **AND** it continues polling until the status changes to `COMPLETED` or `FAILED`

### Scenario 3: Real-time UI update on completion

- **GIVEN** the frontend is actively polling the status of a specific document
- **WHEN** the background worker finishes processing and updates the job and document status in the database
- **AND** the next polling request receives a `COMPLETED` response from the `/documents/{id}/status` endpoint
- **THEN** the frontend immediately stops polling for that document
- **AND** triggers a re-fetch of the main data table or updates the local state to show the success icon and final data for that row
- **AND** optionally displays a brief, non-intrusive toast notification: "Extração de documento X concluída"

### Scenario 4: Error surfacing

- **GIVEN** the background worker encounters an unrecoverable error and marks the job as `FAILED`
- **WHEN** the frontend polling request receives a `FAILED` response from the `/documents/{id}/status` endpoint (along with a potential error message)
- **THEN** the frontend stops polling for that document
- **AND** updates the UI row with an error indicator (e.g., a red warning icon)
- **AND** displays a tooltip or toast notification indicating the failure to the user, allowing them to try uploading the file again
