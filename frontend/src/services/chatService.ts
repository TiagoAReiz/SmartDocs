import api from "@/lib/api";
import type { ChatThread, ChatHistoryMessage, ChatResponse, ChatRequest } from "@/types";

export const chatService = {
  getThreads: async (params: URLSearchParams): Promise<ChatThread[]> => {
    const res = await api.get<ChatThread[]>(`/chat/threads?${params.toString()}`);
    return res.data;
  },
  getMessages: async (threadId: string): Promise<{ messages: ChatHistoryMessage[] }> => {
    const res = await api.get<{ messages: ChatHistoryMessage[] }>(`/chat/threads/${threadId}/messages`);
    return res.data;
  },
  deleteThread: async (threadId: string): Promise<void> => {
    await api.delete(`/chat/threads/${threadId}`);
  },
  sendMessage: async (payload: ChatRequest): Promise<ChatResponse> => {
    const res = await api.post<ChatResponse>("/chat", payload);
    return res.data;
  }
};
