export type ActionType = 'CREATE' | 'UPDATE' | 'DELETE' | 'PROCESS';

export interface AuditLog {
  id: string;
  user_id: number | null;
  user_email: string;
  entity_type: string;
  entity_id: string;
  action_type: ActionType;
  old_values: Record<string, any> | null;
  new_values: Record<string, any> | null;
  ip_address: string | null;
  created_at: string;
}

export interface PaginatedAuditLogsResponse {
  data: AuditLog[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}
