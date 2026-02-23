import { useState, useCallback } from "react";
import { chatService } from "@/services/chatService";
import type { ChatThread } from "@/types";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  data?: Record<string, unknown>[];
  timestamp: Date;
}

const THREADS_PER_PAGE = 20;

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Thread state
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState<string | undefined>(undefined);
  const [isThreadsLoading, setIsThreadsLoading] = useState(false);
  const [threadSearchTerm, setThreadSearchTerm] = useState("");
  const [threadPage, setThreadPage] = useState(0);
  const [hasMoreThreads, setHasMoreThreads] = useState(true);

  const fetchThreads = useCallback(async (page: number, search: string) => {
    setIsThreadsLoading(true);
    try {
      const params = new URLSearchParams({
        limit: THREADS_PER_PAGE.toString(),
        offset: (page * THREADS_PER_PAGE).toString(),
      });
      if (search) {
        params.append("search", search);
      }

      const freshThreads = await chatService.getThreads(params);

      setThreads((prev) => {
        if (page === 0) return freshThreads;
        const newThreads = freshThreads.filter((t) => !prev.some((p) => p.id === t.id));
        return [...prev, ...newThreads];
      });

      setHasMoreThreads(freshThreads.length === THREADS_PER_PAGE);
    } catch (error) {
      console.error("Failed to fetch threads:", error);
    } finally {
      setIsThreadsLoading(false);
    }
  }, []);

  const handleThreadSearch = useCallback(
    (term: string) => {
      setThreadSearchTerm(term);
      setThreadPage(0);
      fetchThreads(0, term);
    },
    [fetchThreads]
  );

  const handleLoadMoreThreads = useCallback(() => {
    if (!hasMoreThreads || isThreadsLoading) return;
    const nextPage = threadPage + 1;
    setThreadPage(nextPage);
    fetchThreads(nextPage, threadSearchTerm);
  }, [hasMoreThreads, isThreadsLoading, threadPage, threadSearchTerm, fetchThreads]);

  const handleSelectThread = async (threadId: string, setShouldAutoScroll?: (v: boolean) => void) => {
    if (threadId === selectedThreadId) return;

    setSelectedThreadId(threadId);
    setIsLoading(true);
    setMessages([]);

    try {
      const res = await chatService.getMessages(threadId);
      const history: Message[] = [];
      res.messages.forEach((msg) => {
        history.push({
          id: `q-${msg.id}`,
          role: "user",
          content: msg.question,
          timestamp: new Date(msg.created_at),
        });
        history.push({
          id: `a-${msg.id}`,
          role: "assistant",
          content: msg.answer,
          data: msg.data,
          timestamp: new Date(msg.created_at),
        });
      });
      setMessages(history);
      if (setShouldAutoScroll) {
          setShouldAutoScroll(true);
      }
    } catch (error) {
      console.error("Failed to fetch thread messages:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = (focusInput?: () => void) => {
    setSelectedThreadId(undefined);
    setMessages([]);
    if (focusInput) {
        setTimeout(focusInput, 100);
    }
  };

  const handleDeleteThread = async (threadId: string, focusInput?: () => void) => {
    if (!confirm("Tem certeza que deseja excluir esta conversa?")) return;
    try {
      await chatService.deleteThread(threadId);
      setThreads((prev) => prev.filter((t) => t.id !== threadId));
      if (selectedThreadId === threadId) {
        handleNewChat(focusInput);
      }
    } catch (error) {
      console.error("Failed to delete thread:", error);
    }
  };

  const handleSend = async (setShouldAutoScroll: (v: boolean) => void, focusInput: () => void) => {
    const question = input.trim();
    if (!question || isLoading) return;

    setShouldAutoScroll(true);
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await chatService.sendMessage({
        question,
        thread_id: selectedThreadId,
      });

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: res.answer,
        data: res.data,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (!selectedThreadId && res.thread_id) {
        setSelectedThreadId(res.thread_id);
        fetchThreads(0, threadSearchTerm);
      } else if (selectedThreadId) {
        fetchThreads(0, threadSearchTerm);
      }
    } catch {
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: "Desculpe, ocorreu um erro ao processar sua pergunta. Tente novamente.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      setTimeout(focusInput, 100);
    }
  };

  return {
    messages,
    setMessages,
    input,
    setInput,
    isLoading,
    threads,
    selectedThreadId,
    isThreadsLoading,
    hasMoreThreads,
    fetchThreads,
    handleThreadSearch,
    handleLoadMoreThreads,
    handleSelectThread,
    handleNewChat,
    handleDeleteThread,
    handleSend,
  };
}
