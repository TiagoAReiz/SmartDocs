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
