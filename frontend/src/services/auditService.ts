import { PaginatedAuditLogsResponse } from '@/types/auditLog';
import api from '@/lib/api';

export interface GetAuditLogsParams {
  page?: number;
  limit?: number;
  email?: string;
  action_type?: string;
  entity_type?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export const auditService = {
  getLogs: async (params?: GetAuditLogsParams): Promise<PaginatedAuditLogsResponse> => {
    const searchParams = new URLSearchParams();
    
    if (params) {
      if (params.page) searchParams.append('page', params.page.toString());
      if (params.limit) searchParams.append('limit', params.limit.toString());
      if (params.email) searchParams.append('email', params.email);
      if (params.action_type) searchParams.append('action_type', params.action_type);
      if (params.entity_type) searchParams.append('entity_type', params.entity_type);
      if (params.sort_by) searchParams.append('sort_by', params.sort_by);
      if (params.sort_order) searchParams.append('sort_order', params.sort_order);
    }

    const queryString = searchParams.toString();
    const url = `/admin/audit-logs${queryString ? `?${queryString}` : ''}`;
    
    const response = await api.get<PaginatedAuditLogsResponse>(url);
    return response.data;
  },
};
