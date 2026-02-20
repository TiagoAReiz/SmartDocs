// ===== User & Auth =====

export interface User {
  id: number;
  name: string;
  email: string;
  role: "admin" | "user";
  created_at?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ===== Documents =====

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

export interface ReprocessResponse {
  id: number;
  status: string;
  message: string;
}

// ===== Chat =====

export interface ChatRequest {
  question: string;
  thread_id?: string;
}

export interface ChatResponse {
  answer: string;
  sql_used: string;
  row_count: number;
  data: Record<string, unknown>[];
  thread_id?: string;
  sources?: Record<string, unknown>[];
}

export interface ChatHistoryMessage {
  id: number;
  question: string;
  answer: string;
  sql_used?: string;
  row_count?: number;
  data?: Record<string, unknown>[];
  created_at: string;
}

export interface ChatThread {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatHistory {
  messages: ChatHistoryMessage[];
}

// ===== Admin =====

export interface CreateUserRequest {
  name: string;
  email: string;
  password: string;
  role: "admin" | "user";
}

export interface UpdateUserRequest {
  name: string;
  email: string;
  role: "admin" | "user";
  password: string | null;
}
