export interface ChatRequest {
  question: string;
  thread_id?: string;
}

export interface RelevantTable {
  index: number;
  row: string[];
  header: string[];
}

export interface ChatDocument {
  id: string | number;
  filename?: string;
  relevant_field_keys: string[];
  relevant_tables: RelevantTable[];
}

export interface StructuredChatResponse {
  message: string;
  final_query?: string;
  documents: ChatDocument[];
}

export interface ChatResponse {
  answer: string;
  sql_used: string;
  row_count: number;
  data: Record<string, unknown>[];
  structured_data?: StructuredChatResponse;
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
  structured_data?: StructuredChatResponse;
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
