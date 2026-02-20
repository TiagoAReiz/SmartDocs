"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import api from "@/lib/api";
import type {
    DocumentDetail,
    PaginatedDocuments,
} from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Search,
    ChevronDown,
    ChevronUp,
    FileText,
    RefreshCw,
    ExternalLink,
    Loader2,
    ChevronLeft,
    ChevronRight,
    Download,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export default function DocumentsPage() {
    const [searchInput, setSearchInput] = useState("");
    const [search, setSearch] = useState("");
    const [statusFilter, setStatusFilter] = useState<string>("all");
    const [page, setPage] = useState(1);
    const [expandedId, setExpandedId] = useState<number | null>(null);
    const [detail, setDetail] = useState<DocumentDetail | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [detailLoading, setDetailLoading] = useState(false);
    const perPage = 20;

    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (statusFilter !== "all") params.set("status_filter", statusFilter);
    params.set("page", String(page));
    params.set("per_page", String(perPage));

    const { data, mutate, isLoading } = useSWR<PaginatedDocuments>(
        `/documents?${params.toString()}`,
        (url: string) => api.get(url).then(r => r.data),
        {
            refreshInterval: (currentData) => {
                if (!currentData) return 0;
                const needsPolling = currentData.documents.some(d => d.status === "uploaded" || d.status === "processing");
                return needsPolling ? 3000 : 0;
            }
        }
    );

    const documents = data?.documents || [];
    const total = data?.total || 0;
    const totalPages = data?.total_pages || 1;
    const loading = isLoading && !data;

    useEffect(() => {
        const t = window.setTimeout(() => {
            setSearch(searchInput.trim());
        }, 500);
        return () => window.clearTimeout(t);
    }, [searchInput]);

    const handleExpand = async (docId: number) => {
        if (expandedId === docId) {
            if (previewUrl) URL.revokeObjectURL(previewUrl);
            setPreviewUrl(null);
            setExpandedId(null);
            setDetail(null);
            return;
        }

        if (previewUrl) URL.revokeObjectURL(previewUrl);
        setPreviewUrl(null);

        setExpandedId(docId);
        setDetailLoading(true);
        try {
            const res = await api.get<DocumentDetail>(`/documents/${docId}`);
            setDetail(res.data);

            // Fetch preview blob if supported
            if (res.data.mime_type === "application/pdf" || res.data.mime_type?.startsWith("image/")) {
                const fileRes = await api.get(`/documents/${docId}/file`, { responseType: "blob" });
                const url = URL.createObjectURL(fileRes.data);
                setPreviewUrl(url);
            }
        } catch {
            toast.error("Erro ao carregar detalhes do documento");
        } finally {
            setDetailLoading(false);
        }
    };

    const handleDownload = async (doc: DocumentDetail) => {
        try {
            if (previewUrl && (doc.mime_type === "application/pdf" || doc.mime_type?.startsWith("image/"))) {
                window.open(previewUrl, "_blank");
                return;
            }

            toast.loading("Baixando documento...");
            const response = await api.get(`/documents/${doc.id}/file`, {
                responseType: "blob",
            });
            const url = window.URL.createObjectURL(new Blob([response.data], { type: doc.mime_type }));
            const link = document.createElement("a");
            link.href = url;
            link.setAttribute("download", doc.filename);
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
            window.URL.revokeObjectURL(url);
            toast.dismiss();
            toast.success("Download iniciado");
        } catch {
            toast.dismiss();
            toast.error("Erro ao baixar documento");
        }
    };

    const handleReprocess = async (docId: number) => {
        try {
            await api.post(`/documents/${docId}/reprocess`);
            toast.success("Reprocessamento iniciado");
            mutate();
        } catch {
            toast.error("Erro ao reprocessar documento");
        }
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
        });
    };

    return (
        <div className="space-y-6">
            <PageHeader
                title="Documentos"
                subtitle={`${total} documento${total !== 1 ? "s" : ""} encontrado${total !== 1 ? "s" : ""}`}
            />

            {/* Filters */}
            <div className="flex flex-col gap-4 rounded-xl border border-white/[0.08] bg-card/50 p-4 backdrop-blur-sm md:flex-row md:items-center">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        placeholder="Buscar por nome..."
                        value={searchInput}
                        onChange={(e) => {
                            setSearchInput(e.target.value);
                            setPage(1);
                        }}
                        className="h-10 border-white/[0.08] bg-white/[0.04] pl-10 text-foreground placeholder:text-muted-foreground focus-visible:ring-primary/20"
                    />
                </div>
                <Select
                    value={statusFilter}
                    onValueChange={(val) => {
                        setStatusFilter(val);
                        setPage(1);
                    }}
                >
                    <SelectTrigger className="h-10 w-full md:w-48 border-white/[0.08] bg-white/[0.04] text-muted-foreground focus:ring-primary/20">
                        <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent className="border-white/[0.08] bg-popover text-popover-foreground">
                        <SelectItem value="all">Todos os status</SelectItem>
                        <SelectItem value="processed">Concluído</SelectItem>
                        <SelectItem value="processing">Processando</SelectItem>
                        <SelectItem value="uploaded">Enviado</SelectItem>
                        <SelectItem value="failed">Falhou</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* Content Area */}
            <div className="space-y-4">
                {/* Mobile View (Cards) */}
                <div className="grid gap-4 md:hidden">
                    {loading
                        ? Array.from({ length: 5 }).map((_, i) => (
                            <div key={i} className="flex flex-col gap-3 rounded-xl border border-white/[0.08] bg-card p-4">
                                <Skeleton className="h-4 w-3/4" />
                                <div className="flex justify-between">
                                    <Skeleton className="h-4 w-20" />
                                    <Skeleton className="h-4 w-20" />
                                </div>
                            </div>
                        ))
                        : documents.map((doc) => (
                            <div
                                key={doc.id}
                                className="flex flex-col rounded-xl border border-white/[0.08] bg-card p-4 shadow-sm transition-all active:scale-[0.99]"
                                onClick={() => handleExpand(doc.id)}
                            >
                                <div className="mb-3 flex items-start justify-between">
                                    <div className="flex flex-1 max-w-40 items-center gap-3 overflow-hidden">
                                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                                            <FileText className="h-5 w-5 text-primary" />
                                        </div>
                                        <div className="min-w-0">
                                            <h4 className="truncate font-medium text-foreground">
                                                {doc.filename}
                                            </h4>
                                            <p className="text-xs text-muted-foreground">
                                                {formatDate(doc.upload_date)} • {doc.page_count} pág
                                            </p>
                                        </div>
                                    </div>
                                    <StatusBadge status={doc.status} />
                                </div>

                                <div className="flex items-center justify-end">
                                    <ChevronDown className={cn("h-5 w-5 text-muted-foreground transition-transform", expandedId === doc.id && "rotate-180")} />
                                </div>

                                {/* Expanded Content Mobile */}
                                {expandedId === doc.id && (
                                    <div className="mt-4 border-t border-white/[0.08] pt-4" onClick={(e) => e.stopPropagation()}>
                                        <ExpandedDocumentDetail
                                            detail={detail}
                                            loading={detailLoading}
                                            previewUrl={previewUrl}
                                            onDownload={() => detail && handleDownload(detail)}
                                            onReprocess={() => detail && handleReprocess(detail.id)}
                                        />
                                    </div>
                                )}
                            </div>
                        ))}
                </div>

                {/* Desktop View (Table) */}
                <div className="hidden overflow-hidden rounded-xl border border-white/[0.08] bg-card/40 backdrop-blur-sm md:block">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
                                <tr>
                                    <th className="px-6 py-4 font-medium">Nome</th>
                                    <th className="px-6 py-4 font-medium">Data</th>
                                    <th className="px-6 py-4 font-medium">Pág.</th>
                                    <th className="px-6 py-4 font-medium">Status</th>
                                    <th className="px-6 py-4 font-medium"></th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/[0.04]">
                                {loading ? (
                                    Array.from({ length: 5 }).map((_, i) => (
                                        <tr key={i}>
                                            <td className="px-6 py-4"><Skeleton className="h-4 w-48" /></td>
                                            <td className="px-6 py-4"><Skeleton className="h-4 w-24" /></td>
                                            <td className="px-6 py-4"><Skeleton className="h-4 w-8" /></td>
                                            <td className="px-6 py-4"><Skeleton className="h-5 w-20" /></td>
                                            <td className="px-6 py-4"></td>
                                        </tr>
                                    ))
                                ) : (
                                    documents.map((doc) => (
                                        <>
                                            <tr
                                                key={doc.id}
                                                onClick={() => handleExpand(doc.id)}
                                                className={cn(
                                                    "cursor-pointer transition-colors hover:bg-muted/50",
                                                    expandedId === doc.id && "bg-muted/30"
                                                )}
                                            >
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center gap-3">
                                                        <FileText className="h-4 w-4 text-primary/70" />
                                                        <span className="font-medium text-foreground">{doc.filename}</span>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-muted-foreground">{formatDate(doc.upload_date)}</td>
                                                <td className="px-6 py-4 text-muted-foreground">{doc.page_count}</td>
                                                <td className="px-6 py-4"><StatusBadge status={doc.status} /></td>
                                                <td className="px-6 py-4 text-muted-foreground">
                                                    <ChevronDown className={cn("h-4 w-4 transition-transform", expandedId === doc.id && "rotate-180")} />
                                                </td>
                                            </tr>
                                            {expandedId === doc.id && (
                                                <tr className="bg-muted/20">
                                                    <td colSpan={5} className="p-0">
                                                        <div className="border-t border-white/[0.04] p-6 shadow-inner">
                                                            <ExpandedDocumentDetail
                                                                detail={detail}
                                                                loading={detailLoading}
                                                                previewUrl={previewUrl}
                                                                onDownload={() => detail && handleDownload(detail)}
                                                                onReprocess={() => detail && handleReprocess(detail.id)}
                                                            />
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                        </>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {!loading && documents.length === 0 && (
                    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.1] bg-white/[0.02] py-20 text-center">
                        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                            <FileText className="h-8 w-8 text-muted-foreground/50" />
                        </div>
                        <h3 className="mt-4 text-lg font-medium text-foreground">Nenhum documento encontrado</h3>
                        <p className="mt-2 text-sm text-muted-foreground">Tente ajustar seus filtros ou faça um novo upload.</p>
                    </div>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                    <div className="flex items-center justify-between border-t border-white/[0.08] pt-4">
                        <span className="text-sm text-muted-foreground">
                            Página {page} de {totalPages}
                        </span>
                        <div className="flex gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                disabled={page <= 1}
                                onClick={() => setPage(page - 1)}
                                className="h-8 border-white/[0.1] bg-transparent hover:bg-white/[0.04]"
                            >
                                <ChevronLeft className="mr-1 h-3 w-3" />
                                Anterior
                            </Button>
                            <Button
                                variant="outline"
                                size="sm"
                                disabled={page >= totalPages}
                                onClick={() => setPage(page + 1)}
                                className="h-8 border-white/[0.1] bg-transparent hover:bg-white/[0.04]"
                            >
                                Próxima
                                <ChevronRight className="ml-1 h-3 w-3" />
                            </Button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

// Extracted Component for Detail View to avoid duplication
function ExpandedDocumentDetail({
    detail,
    loading,
    previewUrl,
    onDownload,
    onReprocess
}: {
    detail: DocumentDetail | null;
    loading: boolean;
    previewUrl: string | null;
    onDownload: () => void;
    onReprocess: () => void;
}) {
    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    if (!detail) return null;

    return (
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
            {/* Preview Section */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-foreground">Preview</h4>
                    <div className="flex gap-2">
                        <Button variant="ghost" size="sm" onClick={onDownload} className="h-8 text-xs hover:bg-white/10">
                            <Download className="mr-2 h-3 w-3" /> Baixar
                        </Button>
                        <Button variant="ghost" size="sm" onClick={onReprocess} className="h-8 text-xs hover:bg-white/10 text-primary">
                            <RefreshCw className="mr-2 h-3 w-3" /> Reprocessar
                        </Button>
                    </div>
                </div>

                <div className="aspect-[3/4] overflow-hidden rounded-lg border border-white/[0.08] bg-black/20">
                    {detail.mime_type === "application/pdf" ? (
                        previewUrl ? (
                            <iframe src={previewUrl} className="h-full w-full" title="PDF Preview" />
                        ) : (
                            <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
                                <Loader2 className="h-6 w-6 animate-spin" />
                                <span className="text-xs">Carregando preview...</span>
                            </div>
                        )
                    ) : detail.mime_type?.startsWith("image/") ? (
                        previewUrl ? (
                            /* eslint-disable-next-line @next/next/no-img-element */
                            <img src={previewUrl} alt="Preview" className="h-full w-full object-contain" />
                        ) : (
                            <div className="flex h-full items-center justify-center text-muted-foreground">
                                <Loader2 className="h-6 w-6 animate-spin" />
                            </div>
                        )
                    ) : (
                        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                            Preview não disponível
                        </div>
                    )}
                </div>
            </div>

            {/* Data Section */}
            <div className="space-y-6">
                <div>
                    <h4 className="mb-3 text-sm font-semibold text-foreground">Dados Extraídos</h4>
                    {detail.fields && detail.fields.length > 0 ? (
                        <div className="grid gap-2">
                            {detail.fields.map((field, i) => (
                                <div key={i} className="flex items-center justify-between rounded-lg border border-white/[0.04] bg-white/[0.02] px-3 py-2.5 transition-colors hover:bg-white/[0.04]">
                                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{field.field_key}</span>
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm text-foreground">{field.field_value}</span>
                                        {field.confidence < 0.8 && (
                                            <span className="text-[10px] text-yellow-500/80" title="Confiança baixa">⚠️</span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-muted-foreground italic">Nenhum campo estruturado encontrado.</p>
                    )}
                </div>

                {detail.tables && detail.tables.length > 0 && (
                    <div>
                        <h4 className="mb-3 text-sm font-semibold text-foreground">Tabelas ({detail.tables.length})</h4>
                        {detail.tables.map((table, tIdx) => (
                            <div key={tIdx} className="mb-4 overflow-x-auto rounded-lg border border-white/[0.08]">
                                <table className="w-full text-xs">
                                    <thead className="bg-white/[0.04]">
                                        <tr>
                                            {table.headers.map((h, i) => (
                                                <th key={i} className="px-3 py-2 text-left font-medium text-muted-foreground">{h}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/[0.04]">
                                        {table.rows.map((row, rIdx) => (
                                            <tr key={rIdx}>
                                                {row.map((cell, cIdx) => (
                                                    <td key={cIdx} className="px-3 py-2 text-foreground/80">{cell}</td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ))}
                    </div>
                )}

                {detail.extracted_text && (
                    <details className="group rounded-lg border border-white/[0.08] bg-white/[0.02]">
                        <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground">
                            Ver Texto Bruto
                        </summary>
                        <div className="border-t border-white/[0.08] bg-black/20 px-4 py-3">
                            <pre className="max-h-60 overflow-auto text-xs leading-relaxed text-muted-foreground/80 whitespace-pre-wrap font-mono">
                                {detail.extracted_text}
                            </pre>
                        </div>
                    </details>
                )}
            </div>
        </div>
    );
}
