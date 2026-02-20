"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import api from "@/lib/api";
import type { ChatResponse, ChatHistoryMessage, ChatThread } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, Bot, User, Menu, Sparkles, StopCircle, Download } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChatSidebar } from "@/components/chat-sidebar";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { ChatDataTable } from "@/components/chat-data-table";

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    data?: Record<string, unknown>[];
    timestamp: Date;
}

const THREADS_PER_PAGE = 20;

export default function ChatPage() {
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

    const scrollViewportRef = useRef<HTMLDivElement>(null);
    const bottomRef = useRef<HTMLDivElement>(null);
    const shouldAutoScrollRef = useRef(true);
    const isAtBottomRef = useRef(true);
    const inputRef = useRef<HTMLInputElement>(null);

    const scrollToBottom = () => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    };

    const handleScroll = () => {
        const el = scrollViewportRef.current;
        if (!el) return;
        isAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
    };

    useEffect(() => {
        if (shouldAutoScrollRef.current || isAtBottomRef.current) {
            scrollToBottom();
            shouldAutoScrollRef.current = false;
        }
    }, [messages.length, isLoading]);

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

            const res = await api.get<ChatThread[]>(`/chat/threads?${params.toString()}`);

            setThreads((prev) => {
                if (page === 0) return res.data;
                // Avoid duplicates
                const newThreads = res.data.filter(t => !prev.some(p => p.id === t.id));
                return [...prev, ...newThreads];
            });

            setHasMoreThreads(res.data.length === THREADS_PER_PAGE);
        } catch (error) {
            console.error("Failed to fetch threads:", error);
        } finally {
            setIsThreadsLoading(false);
        }
    }, []);

    const handleThreadSearch = useCallback((term: string) => {
        setThreadSearchTerm(term);
        setThreadPage(0);
        fetchThreads(0, term);
    }, [fetchThreads]);

    const handleLoadMoreThreads = useCallback(() => {
        if (!hasMoreThreads || isThreadsLoading) return;
        const nextPage = threadPage + 1;
        setThreadPage(nextPage);
        fetchThreads(nextPage, threadSearchTerm);
    }, [hasMoreThreads, isThreadsLoading, threadPage, threadSearchTerm, fetchThreads]);

    const handleSelectThread = async (threadId: string) => {
        if (threadId === selectedThreadId) return;

        setSelectedThreadId(threadId);
        setIsLoading(true);
        setMessages([]);

        try {
            const res = await api.get<{ messages: ChatHistoryMessage[] }>(`/chat/threads/${threadId}/messages`);
            const history: Message[] = [];
            res.data.messages.forEach((msg) => {
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
            shouldAutoScrollRef.current = true;
        } catch (error) {
            console.error("Failed to fetch thread messages:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleNewChat = () => {
        setSelectedThreadId(undefined);
        setMessages([]);
        setTimeout(() => inputRef.current?.focus(), 100);
    };

    const handleDeleteThread = async (threadId: string) => {
        if (!confirm("Tem certeza que deseja excluir esta conversa?")) return;

        try {
            await api.delete(`/chat/threads/${threadId}`);
            setThreads((prev) => prev.filter((t) => t.id !== threadId));
            if (selectedThreadId === threadId) {
                handleNewChat();
            }
        } catch (error) {
            console.error("Failed to delete thread:", error);
        }
    };

    const handleSend = async () => {
        const question = input.trim();
        if (!question || isLoading) return;

        shouldAutoScrollRef.current = true;
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
            const res = await api.post<ChatResponse>("/chat", {
                question,
                thread_id: selectedThreadId
            });

            const assistantMsg: Message = {
                id: `assistant-${Date.now()}`,
                role: "assistant",
                content: res.data.answer,
                data: res.data.data,
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, assistantMsg]);

            if (!selectedThreadId && res.data.thread_id) {
                setSelectedThreadId(res.data.thread_id);
                // Refresh threads to show new one at top
                fetchThreads(0, threadSearchTerm);
            } else if (selectedThreadId) {
                // Ideally move to top, but refreshing list is safer
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
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleExport = (data: Record<string, unknown>[], filename = "export.csv") => {
        if (!data || data.length === 0) return;

        const headers = Object.keys(data[0]);
        const csvContent = [
            headers.join(","),
            ...data.map((row) =>
                headers
                    .map((header) => {
                        const val = row[header];
                        return typeof val === "string" ? `"${val.replace(/"/g, '""')}"` : val;
                    })
                    .join(",")
            ),
        ].join("\n");

        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", filename);
        link.style.visibility = "hidden";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const suggestionChips = [
        "Extrair dados da última fatura",
        "Resumir contratos recentes",
        "Quais documentos vencem hoje?",
        "Analisar cláusulas de rescisão",
    ];

    return (
        <div className="flex h-[calc(100vh-4rem)] overflow-hidden bg-background">
            {/* Sidebar Desktop */}
            <div className="hidden lg:block h-full w-80 border-r border-white/[0.08]">
                <ChatSidebar
                    threads={threads}
                    selectedThreadId={selectedThreadId}
                    onSelectThread={handleSelectThread}
                    onNewChat={handleNewChat}
                    onDeleteThread={handleDeleteThread}
                    isLoading={isThreadsLoading}
                    onSearch={handleThreadSearch}
                    onLoadMore={handleLoadMoreThreads}
                    hasMore={hasMoreThreads}
                />
            </div>

            {/* Main Chat Area */}
            <div className="flex flex-1 flex-col min-w-0 relative">
                {/* Mobile Header with Sidebar Toggle */}
                <div className="lg:hidden flex items-center justify-between p-4 border-b border-white/[0.08] bg-card/80 backdrop-blur-md sticky top-0 z-10">
                    <Sheet>
                        <SheetTrigger asChild>
                            <Button variant="ghost" size="icon" className="text-white hover:bg-white/10">
                                <Menu className="h-5 w-5" />
                            </Button>
                        </SheetTrigger>
                        <SheetContent side="left" className="p-0 border-r border-white/[0.08] w-80 bg-card">
                            <ChatSidebar
                                threads={threads}
                                selectedThreadId={selectedThreadId}
                                onSelectThread={(id) => {
                                    handleSelectThread(id);
                                }}
                                onNewChat={handleNewChat}
                                onDeleteThread={handleDeleteThread}
                                isLoading={isThreadsLoading}
                                onSearch={handleThreadSearch}
                                onLoadMore={handleLoadMoreThreads}
                                hasMore={hasMoreThreads}
                            />
                        </SheetContent>
                    </Sheet>
                    <span className="font-semibold text-white">Chat</span>
                    <Button variant="ghost" size="icon" onClick={handleNewChat}>
                        <Sparkles className="h-4 w-4 text-primary" />
                    </Button>
                </div>

                {/* Messages Container */}
                <div
                    ref={scrollViewportRef}
                    onScroll={handleScroll}
                    className="flex-1 overflow-y-auto px-4 py-6 scroll-smooth"
                >
                    <div className="mx-auto max-w-3xl space-y-8 pb-32">
                        {messages.length === 0 && !isLoading ? (
                            <div className="flex min-h-[50vh] flex-col items-center justify-center text-center animate-in fade-in duration-500">
                                <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-purple-500/20 shadow-lg shadow-primary/10 ring-1 ring-white/10">
                                    <Sparkles className="h-8 w-8 text-primary" />
                                </div>
                                <h3 className="text-xl font-semibold tracking-tight text-foreground">
                                    Como posso ajudar hoje?
                                </h3>
                                <div className="mt-8 grid w-full max-w-lg grid-cols-1 gap-3 sm:grid-cols-2">
                                    {suggestionChips.map((chip) => (
                                        <button
                                            key={chip}
                                            onClick={() => {
                                                setInput(chip);
                                                inputRef.current?.focus();
                                            }}
                                            className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-4 py-3 text-sm text-muted-foreground transition-all hover:border-primary/50 hover:bg-primary/5 hover:text-foreground text-left"
                                        >
                                            {chip}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            messages.map((msg) => (
                                <div
                                    key={msg.id}
                                    className={cn(
                                        "flex w-full gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300",
                                        msg.role === "user" ? "justify-end pl-12" : "justify-start pr-12"
                                    )}
                                >
                                    {msg.role === "assistant" && (
                                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-card border border-white/10 shadow-sm mt-1">
                                            <Bot className="h-4 w-4 text-primary" />
                                        </div>
                                    )}

                                    <div className={cn(
                                        "relative px-5 py-3.5 shadow-sm max-w-full overflow-hidden",
                                        msg.role === "user"
                                            ? "rounded-2xl rounded-tr-sm bg-primary text-primary-foreground"
                                            : "rounded-2xl rounded-tl-sm bg-card border border-white/[0.08] text-card-foreground"
                                    )}>
                                        <div className="prose prose-invert prose-sm max-w-none break-words [&_pre]:bg-black/30 [&_pre]:border [&_pre]:border-white/10">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {msg.content}
                                            </ReactMarkdown>
                                        </div>

                                        {/* Data Table */}
                                        {msg.data && msg.data.length > 0 && (
                                            <ChatDataTable data={msg.data} onExport={handleExport} />
                                        )}

                                        <span className={cn(
                                            "absolute bottom-1 right-3 text-[10px] opacity-50",
                                            msg.role === "user" ? "text-primary-foreground" : "text-muted-foreground"
                                        )}>
                                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    </div>

                                    {msg.role === "user" && (
                                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/20 border border-primary/20 shadow-sm mt-1">
                                            <User className="h-4 w-4 text-primary" />
                                        </div>
                                    )}
                                </div>
                            ))
                        )}

                        {isLoading && (
                            <div className="flex justify-start gap-4 pr-12 animate-in fade-in">
                                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-card border border-white/10 mt-1">
                                    <Bot className="h-4 w-4 text-primary" />
                                </div>
                                <div className="rounded-2xl rounded-tl-sm bg-card border border-white/[0.08] px-5 py-4">
                                    <div className="flex gap-1.5">
                                        <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/50 [animation-delay:-0.3s]" />
                                        <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/50 [animation-delay:-0.15s]" />
                                        <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/50" />
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={bottomRef} className="h-4" />
                    </div>
                </div>

                {/* Input Area */}
                <div className="absolute bottom-0 left-0 right-0 bg-transparent p-4 lg:p-6 bg-gradient-to-t from-background via-background to-transparent pt-10">
                    <div className="mx-auto max-w-3xl">
                        <div className="relative flex items-end gap-2 rounded-2xl bg-card/80 p-2 shadow-2xl backdrop-blur-xl border border-white/[0.08] ring-1 ring-white/[0.05] focus-within:ring-primary/30 transition-shadow hover:shadow-primary/5">
                            <Input
                                ref={inputRef}
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder="Pergunte algo..."
                                className="min-h-[44px] flex-1 border-0 bg-transparent px-2 py-3 text-base shadow-none focus-visible:ring-0 placeholder:text-muted-foreground/50 sm:text-sm"
                                disabled={isLoading}
                                autoComplete="off"
                            />

                            <Button
                                onClick={handleSend}
                                disabled={!input.trim() || isLoading}
                                size="icon"
                                className={cn(
                                    "h-10 w-10 shrink-0 rounded-xl transition-all duration-300",
                                    input.trim()
                                        ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25 hover:scale-105 active:scale-95"
                                        : "bg-muted text-muted-foreground opacity-50"
                                )}
                            >
                                {isLoading ? <StopCircle className="h-5 w-5 animate-pulse" /> : <Send className="h-5 w-5 ml-0.5" />}
                            </Button>
                        </div>
                        <p className="mt-2 text-center text-[10px] text-muted-foreground/40">
                            IA generativa pode cometer erros. Verifique informações importantes.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
