"use client";

import { useState, useEffect } from "react";
import { Plus, Trash2, MessageSquare, Search, MoreHorizontal, Bot, ChevronDown } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChatThread } from "@/lib/types";
import { useDebounce } from "@/hooks/use-debounce";

interface ChatSidebarProps extends React.HTMLAttributes<HTMLDivElement> {
    threads: ChatThread[];
    selectedThreadId?: string;
    onSelectThread: (id: string) => void;
    onNewChat: () => void;
    onDeleteThread: (id: string) => void;
    onSearch: (term: string) => void;
    onLoadMore: () => void;
    hasMore: boolean;
    isLoading?: boolean;
}

export function ChatSidebar({
    threads,
    selectedThreadId,
    onSelectThread,
    onNewChat,
    onDeleteThread,
    onSearch,
    onLoadMore,
    hasMore,
    isLoading,
    className,
    ...props
}: ChatSidebarProps) {
    const [searchTerm, setSearchTerm] = useState("");
    const debouncedSearchTerm = useDebounce(searchTerm, 500);

    useEffect(() => {
        onSearch(debouncedSearchTerm);
    }, [debouncedSearchTerm, onSearch]);

    return (
        <div className={cn("flex h-full w-80 flex-col border-r border-white/[0.08] bg-card/30 backdrop-blur-sm", className)} {...props}>
            <div className="p-4 space-y-4">
                <Button
                    onClick={onNewChat}
                    className="w-full justify-start gap-2 h-10 shadow-lg shadow-primary/20 transition-all hover:scale-[1.02]"
                >
                    <Plus className="h-4 w-4" />
                    Nova conversa
                </Button>

                <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        placeholder="Buscar historico..."
                        className="h-9 pl-9 border-white/[0.08] bg-white/[0.04] text-foreground placeholder:text-muted-foreground focus-visible:ring-primary/20"
                    />
                </div>
            </div>

            <div className="flex-1 overflow-hidden">
                <ScrollArea className="h-full">
                    <div className="px-3 pb-4">
                        {threads.length === 0 && !isLoading ? (
                            <div className="flex flex-col items-center justify-center p-8 text-center text-sm text-muted-foreground">
                                <MessageSquare className="mb-2 h-8 w-8 opacity-20" />
                                {searchTerm ? "Nenhuma conversa encontrada" : "Histórico vazio"}
                            </div>
                        ) : (
                            <div className="space-y-1">
                                <h3 className="px-2 pb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">
                                    Histórico
                                </h3>
                                {threads.map((thread) => (
                                    <button
                                        key={thread.id}
                                        onClick={() => onSelectThread(thread.id)}
                                        className={cn(
                                            "group flex w-full items-center justify-between rounded-lg px-3 py-3 text-left transition-all hover:bg-white/[0.04]",
                                            selectedThreadId === thread.id
                                                ? "bg-primary/10 hover:bg-primary/15"
                                                : "text-muted-foreground"
                                        )}
                                    >
                                        <div className="flex flex-1 items-start gap-3 overflow-hidden">
                                            <MessageSquare className={cn(
                                                "mt-0.5 h-4 w-4 shrink-0 transition-colors",
                                                selectedThreadId === thread.id ? "text-primary" : "text-muted-foreground/50 group-hover:text-muted-foreground"
                                            )} />
                                            <div className="flex flex-col min-w-0 overflow-hidden gap-0.5">
                                                <span className={cn(
                                                    "truncate text-sm font-medium transition-colors",
                                                    selectedThreadId === thread.id ? "text-foreground" : "text-muted-foreground group-hover:text-foreground"
                                                )}>
                                                    {thread.title || "Nova conversa"}
                                                </span>
                                                <span className="truncate text-[10px] text-muted-foreground/60">
                                                    {thread.updated_at ? formatDistanceToNow(new Date(thread.updated_at), {
                                                        addSuffix: true,
                                                        locale: ptBR,
                                                    }) : 'Recentemente'}
                                                </span>
                                            </div>
                                        </div>

                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <div
                                                    className={cn(
                                                        "flex h-6 w-6 items-center justify-center rounded-md opacity-0 transition-opacity hover:bg-white/10 group-hover:opacity-100",
                                                        selectedThreadId === thread.id && "opacity-100"
                                                    )}
                                                    onClick={(e) => e.stopPropagation()}
                                                >
                                                    <MoreHorizontal className="h-3.5 w-3.5 text-muted-foreground" />
                                                </div>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end" className="w-48 bg-card border-white/[0.08]">
                                                <DropdownMenuItem
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        onDeleteThread(thread.id);
                                                    }}
                                                    className="text-red-400 focus:text-red-400 focus:bg-red-500/10 cursor-pointer"
                                                >
                                                    <Trash2 className="mr-2 h-4 w-4" />
                                                    Excluir conversa
                                                </DropdownMenuItem>
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </button>
                                ))}

                                {hasMore && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="w-full text-xs text-muted-foreground hover:text-foreground mt-2"
                                        onClick={onLoadMore}
                                        disabled={isLoading}
                                    >
                                        {isLoading ? "Carregando..." : "Carregar mais"}
                                        {!isLoading && <ChevronDown className="ml-1 h-3 w-3" />}
                                    </Button>
                                )}
                            </div>
                        )}

                        {isLoading && threads.length === 0 && (
                            <div className="flex flex-col items-center justify-center p-8 text-center text-sm text-muted-foreground animate-pulse">
                                <Bot className="mb-2 h-8 w-8 opacity-20" />
                                Carregando...
                            </div>
                        )}
                    </div>
                </ScrollArea>
            </div>
        </div>
    );
}
