import api from "@/lib/api";
import type { UploadResponse, DocumentDetail, PaginatedDocuments } from "@/types";

export const documentService = {
  uploadFiles: async (files: File[]): Promise<UploadResponse> => {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    const res = await api.post<UploadResponse>("/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" }
    });
    return res.data;
  },
  checkStatus: async (documentId: number): Promise<{ status: string }> => {
    const res = await api.get<{ status: string }>(`/documents/${documentId}/status`);
    return res.data;
  },
  reprocess: async (documentId: number): Promise<void> => {
    await api.post(`/documents/${documentId}/reprocess`);
  },
  getDocuments: async (params: URLSearchParams): Promise<PaginatedDocuments> => {
    const res = await api.get<PaginatedDocuments>(`/documents?${params.toString()}`);
    return res.data;
  },
  getDocument: async (documentId: number): Promise<DocumentDetail> => {
    const res = await api.get<DocumentDetail>(`/documents/${documentId}`);
    return res.data;
  },
  downloadFile: async (documentId: number): Promise<Blob> => {
    const res = await api.get(`/documents/${documentId}/file`, { responseType: "blob" });
    return res.data;
  },
  deleteDocument: async (documentId: number): Promise<void> => {
    await api.delete(`/documents/${documentId}`);
  }
};
