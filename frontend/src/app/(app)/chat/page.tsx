"use client";

import { useState, useRef, useEffect } from "react";
import { useChat } from "@/hooks/useChat";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, Bot, User, Menu, Sparkles, StopCircle, PanelLeftClose, PanelLeftOpen, FileText, Download } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { type Message } from "@/hooks/useChat";
import { ChatSidebar } from "@/components/chat-sidebar";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { ChatDataTable } from "@/components/chat-data-table";

export default function ChatPage() {
    const {
        messages,
        input,
        setInput,
        isLoading,
        threads,
        selectedThreadId,
        isThreadsLoading,
        hasMoreThreads,
        handleThreadSearch,
        handleLoadMoreThreads,
        handleSelectThread,
        handleNewChat,
        handleDeleteThread,
        handleSend,
    } = useChat();

    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
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

    const setShouldAutoScroll = (v: boolean) => {
        shouldAutoScrollRef.current = v;
    };

    const focusInput = () => {
        inputRef.current?.focus();
    };

    const onSelectThread = (id: string) => {
        handleSelectThread(id, setShouldAutoScroll);
    };

    const onNewChat = () => {
        handleNewChat(focusInput);
    };

    const onDeleteThread = (id: string) => {
        handleDeleteThread(id, focusInput);
    };

    const onSend = () => {
        handleSend(setShouldAutoScroll, focusInput);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            onSend();
        }
    };

    const handleExport = (msg: Message) => {
        const d = new Date();
        const dateStr = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
        const filename = `smartdocs-export-${dateStr}.csv`;

        let csvContent = "";

        // Se tem dados estruturados, vamos exportar as tabelas
        if (msg.structured_data?.documents) {
            msg.structured_data.documents.forEach((doc, idx: number) => {
                if (doc.relevant_tables && doc.relevant_tables.length > 0) {
                    if (idx > 0) csvContent += "\n\n";
                    csvContent += `Documento: ${doc.filename || doc.id}\n`;

                    doc.relevant_tables.forEach((table, tIdx: number) => {
                        if (tIdx > 0) csvContent += "\n";
                        csvContent += table.header.map((h: string) => `"${String(h).replace(/"/g, '""')}"`).join(",") + "\n";
                        table.row.forEach((row: unknown) => {
                            // Supondo que 'row' aqui seja um array (de fato deveria ser um array de arrays, mas nosso schema tem row: list[str] o que indica uma única linha ou precisamos processar melhor)
                            // Na verdade, se row for string[], são os valores. Se precisarmos de múltiplas rows, o backend deveria emitir 'rows: list[list[str]]'.
                            // Se for array simples, unimos.
                            if (Array.isArray(row)) {
                                csvContent += row.map((val: unknown) => `"${String(val).replace(/"/g, '""')}"`).join(",") + "\n";
                            } else {
                                csvContent += `"${String(row).replace(/"/g, '""')}"\n`;
                            }
                        });
                    });
                }
            });
        }
        // Fallback antigo
        else if (msg.data && msg.data.length > 0) {
            const headers = Object.keys(msg.data[0]);
            csvContent = [
                headers.join(","),
                ...msg.data.map((row: Record<string, unknown>) =>
                    headers
                        .map((header: string) => {
                            const val = row[header];
                            return typeof val === "string" ? `"${val.replace(/"/g, '""')}"` : val;
                        })
                        .join(",")
                ),
            ].join("\n");
        }

        if (!csvContent) return;

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
            <div className={cn(
                "hidden lg:block h-full border-r border-white/[0.08] transition-[width,opacity] duration-300 ease-in-out shrink-0",
                isSidebarOpen ? "w-80 opacity-100" : "w-0 opacity-0 overflow-hidden border-none"
            )}>
                <div className="w-80 h-full">
                    <ChatSidebar
                        threads={threads}
                        selectedThreadId={selectedThreadId}
                        onSelectThread={onSelectThread}
                        onNewChat={onNewChat}
                        onDeleteThread={onDeleteThread}
                        isLoading={isThreadsLoading}
                        onSearch={handleThreadSearch}
                        onLoadMore={handleLoadMoreThreads}
                        hasMore={hasMoreThreads}
                    />
                </div>
            </div>

            {/* Main Chat Area */}
            <div className="flex flex-1 flex-col min-w-0 relative">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-white/[0.08] bg-card/80 backdrop-blur-md sticky top-0 z-10 transition-all duration-300">
                    <div className="flex items-center gap-2">
                        {/* Mobile Sidebar Toggle */}
                        <div className="lg:hidden">
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
                                        onSelectThread={onSelectThread}
                                        onNewChat={onNewChat}
                                        onDeleteThread={onDeleteThread}
                                        isLoading={isThreadsLoading}
                                        onSearch={handleThreadSearch}
                                        onLoadMore={handleLoadMoreThreads}
                                        hasMore={hasMoreThreads}
                                    />
                                </SheetContent>
                            </Sheet>
                        </div>

                        {/* Desktop Sidebar Toggle */}
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                            className="hidden lg:flex text-muted-foreground hover:text-foreground hover:bg-white/10"
                            title={isSidebarOpen ? "Ocultar histórico" : "Mostrar histórico"}
                        >
                            {isSidebarOpen ? <PanelLeftClose className="h-5 w-5" /> : <PanelLeftOpen className="h-5 w-5" />}
                        </Button>
                        <span className="font-semibold text-white">Chat</span>
                    </div>

                    <Button variant="ghost" size="icon" onClick={onNewChat} className="text-muted-foreground hover:text-foreground hover:bg-white/10" title="Nova conversa">
                        <Sparkles className="h-4 w-4 text-primary" />
                    </Button>
                </div>

                {/* Messages Container */}
                <div
                    ref={scrollViewportRef}
                    onScroll={handleScroll}
                    className="flex-1 overflow-y-auto px-4 py-6 lg:px-8 lg:py-8 scroll-smooth"
                >
                    <div className="w-full space-y-8 pb-32 transition-all duration-300">
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
                                                focusInput();
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

                                        {/* Nested Structured Document Data */}
                                        {msg.structured_data?.documents && msg.structured_data.documents.length > 0 ? (
                                            <div className="mt-4 space-y-4">
                                                {msg.structured_data.documents.map((doc: import("@/types").ChatDocument, docIdx: number) => (
                                                    <div key={docIdx} className="bg-black/10 border border-white/10 rounded-xl overflow-hidden">
                                                        <div className="bg-white/5 px-4 py-2 text-xs font-semibold text-primary/80 flex justify-between items-center shadow-sm">
                                                            <div className="flex items-center gap-2">
                                                                <FileText className="w-3.5 h-3.5" />
                                                                {doc.filename || `Documento ${doc.id}`}
                                                            </div>
                                                            {/* Only show export for the first document context button to export everything in this message */}
                                                            {docIdx === 0 && (
                                                                <Button
                                                                    variant="ghost"
                                                                    size="icon"
                                                                    className="h-6 w-6 hover:bg-white/10 text-muted-foreground"
                                                                    title="Exportar dados deste balão"
                                                                    onClick={() => handleExport(msg)}
                                                                >
                                                                    <Download className="h-3 w-3" />
                                                                </Button>
                                                            )}
                                                        </div>
                                                        <div className="p-0">
                                                            {/* Fields Key-Value Pairs */}
                                                            {doc.relevant_field_keys && doc.relevant_field_keys.length > 0 && (
                                                                <div className="p-3">
                                                                    <div className="flex flex-wrap gap-2">
                                                                        {doc.relevant_field_keys.map((field: string, fIdx: number) => (
                                                                            <span key={fIdx} className="px-2 py-1 bg-white/5 border border-white/[0.08] rounded text-xs text-foreground/80 break-words max-w-full">
                                                                                {field}
                                                                            </span>
                                                                        ))}
                                                                    </div>
                                                                </div>
                                                            )}

                                                            {/* Structured Tables */}
                                                            {(() => {
                                                                const validTables = (doc.relevant_tables || []).filter((table: import("@/types").RelevantTable) =>
                                                                    !table.row.some(val =>
                                                                        val === null ||
                                                                        val === undefined ||
                                                                        String(val).trim() === '' ||
                                                                        String(val).toLowerCase() === 'null' ||
                                                                        String(val).toLowerCase() === 'none'
                                                                    )
                                                                );

                                                                if (validTables.length === 0) return null;

                                                                return (
                                                                    <div className="border-t border-white/5 bg-black/5">
                                                                        {validTables.map((table: import("@/types").RelevantTable, tIdx: number) => (
                                                                            <div key={`table-${tIdx}`} className="overflow-x-auto">
                                                                                <table className="w-full text-sm text-left">
                                                                                    <thead className="bg-white/5 text-xs uppercase text-muted-foreground">
                                                                                        <tr>
                                                                                            {table.header.map((col: string, cIdx: number) => (
                                                                                                <th key={`th-${cIdx}`} className="px-4 py-2 font-medium break-words min-w-[100px] max-w-[200px] border-b border-white/5">{col}</th>
                                                                                            ))}
                                                                                        </tr>
                                                                                    </thead>
                                                                                    <tbody>
                                                                                        {/* Safety check as backend SQL tool might return rows differently */}
                                                                                        <tr className="border-b border-white/5 last:border-0 hover:bg-white/[0.02]">
                                                                                            {table.row.map((val: unknown, vIdx: number) => (
                                                                                                <td key={`td-${vIdx}`} className="px-4 py-2 break-words min-w-[100px] max-w-[200px]">{String(val)}</td>
                                                                                            ))}
                                                                                        </tr>
                                                                                    </tbody>
                                                                                </table>
                                                                            </div>
                                                                        ))}
                                                                    </div>
                                                                );
                                                            })()}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            /* Legacy Data Table fallback */
                                            msg.data && msg.data.length > 0 && (
                                                <ChatDataTable data={msg.data} onExport={() => handleExport(msg)} />
                                            )
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
                <div className="absolute bottom-0 left-0 right-0 bg-transparent p-4 lg:p-8 bg-gradient-to-t from-background via-background to-transparent pt-10">
                    <div className="w-full transition-all duration-300">
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
                                onClick={onSend}
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
