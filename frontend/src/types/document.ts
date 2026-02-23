export type DocumentStatus = "uploaded" | "processing" | "processed" | "failed";

export interface Document {
  id: number;
  filename: string;
  original_extension: string;
  upload_date: string;
  page_count: number;
  status: DocumentStatus;
}

export interface ExtractedField {
  field_key: string;
  field_value: string;
  confidence: number;
  page_number: number;
}

export interface ExtractedTable {
  table_index: number;
  page_number: number;
  headers: string[];
  rows: string[][];
}

export interface DocumentDetail extends Document {
  mime_type: string;
  blob_url: string;
  extracted_text: string;
  fields: ExtractedField[];
  tables: ExtractedTable[];
  error_message: string | null;
}

export interface PaginatedDocuments {
  documents: Document[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface UploadResponse {
  documents: {
    id: number;
    filename: string;
    status: string;
    created_at: string;
  }[];
}

export interface DocumentProcessingJobResponse {
  id: string;
  document_id: number;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  attempts: number;
  error_log: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ReprocessResponse {
  id: number;
  status: string;
  message: string;
}
