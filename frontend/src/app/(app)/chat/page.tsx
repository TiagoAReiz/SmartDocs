"use client";

import { useState, useRef, useEffect } from "react";
import api from "@/lib/api";
import type { ChatResponse, ChatHistoryMessage } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Loader2, Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    data?: Record<string, unknown>[];
    timestamp: Date;
}

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, isLoading]);

    // Load chat history on mount
    useEffect(() => {
        api
            .get<{ messages: ChatHistoryMessage[] }>("/chat/history?limit=50")
            .then((res) => {
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
                        timestamp: new Date(msg.created_at),
                    });
                });
                setMessages(history);
            })
            .catch(() => {
                // History endpoint is optional
            });
    }, []);

    const handleSend = async () => {
        const question = input.trim();
        if (!question || isLoading) return;

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
            const res = await api.post<ChatResponse>("/chat", { question });
            const assistantMsg: Message = {
                id: `assistant-${Date.now()}`,
                role: "assistant",
                content: res.data.answer,
                data: res.data.data,
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, assistantMsg]);
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
            inputRef.current?.focus();
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex h-[calc(100vh-3rem)] flex-col lg:h-[calc(100vh-4rem)]">
            <PageHeader
                title="Chat"
                subtitle="Converse com seus documentos em linguagem natural"
            />

            {/* Messages area */}
            <Card className="mt-6 flex flex-1 flex-col overflow-hidden border-white/[0.06] bg-[#0B1120]">
                <ScrollArea className="flex-1 p-4 lg:p-6" ref={scrollRef}>
                    {messages.length === 0 && !isLoading && (
                        <div className="flex h-full flex-col items-center justify-center py-20 text-center">
                            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#136dec]/10">
                                <Bot className="h-8 w-8 text-[#136dec]" />
                            </div>
                            <h3 className="text-lg font-medium text-slate-300">
                                Olá! Como posso ajudar?
                            </h3>
                            <p className="mt-2 max-w-md text-sm text-slate-500">
                                Faça perguntas sobre seus documentos em linguagem natural.
                                Por exemplo: &quot;Quais contratos vencem nos próximos 30 dias?&quot;
                            </p>
                        </div>
                    )}

                    <div className="space-y-4">
                        {messages.map((msg) => (
                            <div
                                key={msg.id}
                                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                            >
                                <div
                                    className={`flex max-w-[80%] gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                                >
                                    <div
                                        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${msg.role === "user"
                                                ? "bg-[#136dec]"
                                                : "bg-slate-700"
                                            }`}
                                    >
                                        {msg.role === "user" ? (
                                            <User className="h-4 w-4 text-white" />
                                        ) : (
                                            <Bot className="h-4 w-4 text-slate-300" />
                                        )}
                                    </div>
                                    <div
                                        className={`rounded-2xl px-4 py-3 ${msg.role === "user"
                                                ? "bg-[#136dec] text-white"
                                                : "bg-[#1E293B] text-slate-200"
                                            }`}
                                    >
                                        <div className="prose prose-invert prose-sm max-w-none [&_table]:w-full [&_table]:border-collapse [&_th]:border [&_th]:border-white/10 [&_th]:bg-white/5 [&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_th]:text-xs [&_th]:font-medium [&_th]:text-slate-300 [&_td]:border [&_td]:border-white/10 [&_td]:px-3 [&_td]:py-2 [&_td]:text-sm [&_td]:text-slate-400">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {msg.content}
                                            </ReactMarkdown>
                                        </div>
                                        {/* Render data table if present */}
                                        {msg.data && msg.data.length > 0 && (
                                            <div className="mt-3 overflow-x-auto rounded-lg border border-white/[0.06]">
                                                <table className="w-full text-sm">
                                                    <thead>
                                                        <tr className="border-b border-white/[0.06] bg-white/[0.03]">
                                                            {Object.keys(msg.data[0]).map((key) => (
                                                                <th
                                                                    key={key}
                                                                    className="px-3 py-2 text-left text-xs font-medium text-slate-400"
                                                                >
                                                                    {key}
                                                                </th>
                                                            ))}
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {msg.data.map((row, i) => (
                                                            <tr
                                                                key={i}
                                                                className="border-b border-white/[0.04] last:border-0"
                                                            >
                                                                {Object.values(row).map((val, j) => (
                                                                    <td
                                                                        key={j}
                                                                        className="px-3 py-2 text-slate-300"
                                                                    >
                                                                        {String(val)}
                                                                    </td>
                                                                ))}
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}

                        {/* Typing indicator */}
                        {isLoading && (
                            <div className="flex justify-start">
                                <div className="flex gap-3">
                                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-700">
                                        <Bot className="h-4 w-4 text-slate-300" />
                                    </div>
                                    <div className="flex items-center gap-1.5 rounded-2xl bg-[#1E293B] px-4 py-3">
                                        <div className="h-2 w-2 animate-bounce rounded-full bg-slate-500 [animation-delay:0ms]" />
                                        <div className="h-2 w-2 animate-bounce rounded-full bg-slate-500 [animation-delay:150ms]" />
                                        <div className="h-2 w-2 animate-bounce rounded-full bg-slate-500 [animation-delay:300ms]" />
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </ScrollArea>

                {/* Input bar */}
                <div className="border-t border-white/[0.06] p-4">
                    <div className="flex gap-3">
                        <Input
                            ref={inputRef}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Pergunte algo sobre seus documentos..."
                            className="h-11 flex-1 border-white/[0.08] bg-white/[0.04] text-slate-200 placeholder:text-slate-600 focus:border-[#136dec]/50"
                            disabled={isLoading}
                        />
                        <Button
                            onClick={handleSend}
                            disabled={isLoading || !input.trim()}
                            className="h-11 w-11 bg-[#136dec] p-0 text-white shadow-lg shadow-[#136dec]/20 transition-all hover:bg-[#1178ff] disabled:opacity-40"
                        >
                            {isLoading ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Send className="h-4 w-4" />
                            )}
                        </Button>
                    </div>
                </div>
            </Card>
        </div>
    );
}
