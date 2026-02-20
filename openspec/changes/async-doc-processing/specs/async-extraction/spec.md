# Spec: async-extraction

## Scenarios

### Scenario 1: Uploading a new PDF document

- **GIVEN** a user uploads a valid PDF document via the POST `/documents` endpoint
- **WHEN** the backend receives the file
- **THEN** it successfully pushes the file to Azure Blob Storage
- **AND** it creates a record in the `documents` table with a provisional status (e.g., "Processing")
- **AND** it creates a job record in the `document_processing_jobs` table assigned to the document ID with status `PENDING`
- **AND** it returns an immediate HTTP 200 response to the user with the document metadata

### Scenario 2: Background worker picking up a job

- **GIVEN** there is a pending job in the `document_processing_jobs` table
- **WHEN** the background worker queries for new jobs (polling)
- **THEN** it locks the job record exclusively using `SELECT ... FOR UPDATE SKIP LOCKED`
- **AND** it updates the job status to `PROCESSING` and sets the `started_at` timestamp

### Scenario 3: Successful document extraction by the worker

- **GIVEN** the background worker has locked a job and is processing it
- **WHEN** the call to Azure Document Intelligence succeeds and returns the extracted JSON
- **THEN** the worker processes the chunks and generates OpenAI embeddings
- **AND** it saves the data into `document_fields` and updates the pgvector data in `documents`
- **AND** it updates the job status in `document_processing_jobs` to `COMPLETED` and sets the `completed_at` timestamp
- **AND** it updates the document status in the `documents` table to reflect successful processing (if applicable)

### Scenario 4: Handling extraction failures (Rate Limit / Timeout)

- **GIVEN** the background worker has locked a job and is making a request to Azure Document Intelligence
- **WHEN** the Azure API returns an error or times out
- **THEN** the worker catches the exception
- **AND** increments the `attempts` counter for that job in the database
- **AND** updates the job status back to `PENDING` (if attempts under threshold) or `FAILED` (if max attempts reached)
- **AND** logs the error details in the `error_log` field

### Scenario 5: Handling worker crashes (Zombie jobs)

- **GIVEN** a job was marked as `PROCESSING` but the worker process crashed before completion
- **WHEN** a watchdog routine or the main polling loop identifies a job stuck in `PROCESSING` for longer than a predefined threshold (e.g., 2 hours) based on `started_at`
- **THEN** the system safely resets the job status back to `PENDING`
- **AND** increments the `attempts` counter to allow another worker to retry it
