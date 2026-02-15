"use client";

import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import type {
    Document,
    DocumentDetail,
    PaginatedDocuments,
    DocumentStatus,
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
} from "lucide-react";
import { toast } from "sonner";

export default function DocumentsPage() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [statusFilter, setStatusFilter] = useState<string>("all");
    const [page, setPage] = useState(1);
    const [total, setTotal] = useState(0);
    const [totalPages, setTotalPages] = useState(1);
    const [expandedId, setExpandedId] = useState<number | null>(null);
    const [detail, setDetail] = useState<DocumentDetail | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [detailLoading, setDetailLoading] = useState(false);
    const perPage = 20;

    const fetchDocuments = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (search) params.set("search", search);
            if (statusFilter !== "all") params.set("status", statusFilter);
            params.set("page", String(page));
            params.set("per_page", String(perPage));

            const res = await api.get<PaginatedDocuments>(
                `/documents?${params.toString()}`
            );
            setDocuments(res.data.documents);
            setTotal(res.data.total);
            setTotalPages(res.data.total_pages);
        } catch {
            toast.error("Erro ao carregar documentos");
        } finally {
            setLoading(false);
        }
    }, [search, statusFilter, page]);

    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

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
            // Use existing preview URL if available
            if (previewUrl && (doc.mime_type === "application/pdf" || doc.mime_type?.startsWith("image/"))) {
                window.open(previewUrl, "_blank");
                return;
            }

            // Otherwise fetch blob with auth
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
            fetchDocuments();
        } catch {
            toast.error("Erro ao reprocessar documento");
        }
    };

    const typeColors: Record<string, string> = {
        contrato: "bg-blue-500/15 text-blue-400 border-blue-500/20",
        relatorio: "bg-purple-500/15 text-purple-400 border-purple-500/20",
        nota_fiscal: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
        default: "bg-slate-500/15 text-slate-400 border-slate-500/20",
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
        });
    };

    return (
        <div>
            <PageHeader
                title="Documentos"
                subtitle={`${total} documento${total !== 1 ? "s" : ""} encontrado${total !== 1 ? "s" : ""}`}
            />

            {/* Filters */}
            <Card className="mt-6 flex flex-wrap items-center gap-4 border-white/[0.06] bg-[#1E293B]/50 p-4">
                <div className="relative flex-1 min-w-[200px]">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                    <Input
                        placeholder="Buscar por nome..."
                        value={search}
                        onChange={(e) => {
                            setSearch(e.target.value);
                            setPage(1);
                        }}
                        className="h-10 border-white/[0.08] bg-white/[0.04] pl-10 text-slate-200 placeholder:text-slate-600"
                    />
                </div>
                <Select
                    value={statusFilter}
                    onValueChange={(val) => {
                        setStatusFilter(val);
                        setPage(1);
                    }}
                >
                    <SelectTrigger className="h-10 w-44 border-white/[0.08] bg-white/[0.04] text-slate-300">
                        <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent className="border-white/[0.08] bg-[#1E293B]">
                        <SelectItem value="all">Todos os status</SelectItem>
                        <SelectItem value="processed">Concluído</SelectItem>
                        <SelectItem value="processing">Processando</SelectItem>
                        <SelectItem value="uploaded">Enviado</SelectItem>
                        <SelectItem value="failed">Falhou</SelectItem>
                    </SelectContent>
                </Select>
            </Card>

            {/* Documents table */}
            <div className="mt-4 overflow-hidden rounded-xl border border-white/[0.06]">
                {/* Header */}
                <div className="grid grid-cols-[1fr_120px_120px_80px_100px_40px] gap-4 border-b border-white/[0.06] bg-[#1E293B]/80 px-4 py-3 text-xs font-medium uppercase tracking-wider text-slate-500">
                    <span>Nome</span>
                    <span>Tipo</span>
                    <span>Data Upload</span>
                    <span>Páginas</span>
                    <span>Status</span>
                    <span />
                </div>

                {/* Loading state */}
                {loading && (
                    <div className="space-y-0">
                        {Array.from({ length: 5 }).map((_, i) => (
                            <div
                                key={i}
                                className="grid grid-cols-[1fr_120px_120px_80px_100px_40px] gap-4 border-b border-white/[0.04] px-4 py-4"
                            >
                                <Skeleton className="h-4 w-48" />
                                <Skeleton className="h-5 w-20" />
                                <Skeleton className="h-4 w-24" />
                                <Skeleton className="h-4 w-8" />
                                <Skeleton className="h-5 w-20" />
                                <Skeleton className="h-4 w-4" />
                            </div>
                        ))}
                    </div>
                )}

                {/* Rows */}
                {!loading &&
                    documents.map((doc) => (
                        <div key={doc.id}>
                            <div
                                onClick={() => handleExpand(doc.id)}
                                className="grid cursor-pointer grid-cols-[1fr_120px_120px_80px_100px_40px] items-center gap-4 border-b border-white/[0.04] px-4 py-4 transition-colors hover:bg-white/[0.02]"
                            >
                                <div className="flex items-center gap-3 min-w-0">
                                    <FileText className="h-4 w-4 shrink-0 text-slate-500" />
                                    <span className="truncate text-sm font-medium text-slate-200">
                                        {doc.filename}
                                    </span>
                                </div>
                                <Badge
                                    variant="outline"
                                    className={`text-xs ${typeColors[doc.type] || typeColors.default}`}
                                >
                                    {doc.type}
                                </Badge>
                                <span className="text-sm text-slate-400">
                                    {formatDate(doc.upload_date)}
                                </span>
                                <span className="text-sm text-slate-400">
                                    {doc.page_count}
                                </span>
                                <StatusBadge status={doc.status} />
                                <div className="text-slate-500">
                                    {expandedId === doc.id ? (
                                        <ChevronUp className="h-4 w-4" />
                                    ) : (
                                        <ChevronDown className="h-4 w-4" />
                                    )}
                                </div>
                            </div>

                            {/* Expanded detail */}
                            {expandedId === doc.id && (
                                <div className="border-b border-white/[0.06] bg-[#0B1120]/50 p-6">
                                    {detailLoading ? (
                                        <div className="flex items-center justify-center py-8">
                                            <Loader2 className="h-6 w-6 animate-spin text-[#136dec]" />
                                        </div>
                                    ) : detail ? (
                                        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                                            {/* Document preview */}
                                            <div>
                                                <h4 className="mb-3 text-sm font-medium text-slate-300">
                                                    Preview do Documento
                                                </h4>
                                                <div className="aspect-[4/3] overflow-hidden rounded-lg border border-white/[0.06] bg-white/[0.02]">
                                                    {detail.mime_type === "application/pdf" ? (
                                                        previewUrl ? (
                                                            <iframe
                                                                src={previewUrl}
                                                                className="h-full w-full"
                                                                title={detail.filename}
                                                            />
                                                        ) : (
                                                            <div className="flex h-full items-center justify-center">
                                                                <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
                                                            </div>
                                                        )
                                                    ) : detail.mime_type?.startsWith("image/") ? (
                                                        previewUrl ? (
                                                            /* eslint-disable-next-line @next/next/no-img-element */
                                                            <img
                                                                src={previewUrl}
                                                                alt={detail.filename}
                                                                className="h-full w-full object-contain"
                                                            />
                                                        ) : (
                                                            <div className="flex h-full items-center justify-center">
                                                                <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
                                                            </div>
                                                        )
                                                    ) : (
                                                        <div className="flex h-full items-center justify-center text-sm text-slate-500">
                                                            Preview não disponível para este tipo de arquivo
                                                        </div>
                                                    )}
                                                </div>
                                                <div className="mt-3 flex gap-2">
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        onClick={() => handleDownload(detail)}
                                                        className="border-white/[0.1] text-slate-300 hover:bg-white/[0.04]"
                                                    >
                                                        <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                                                        Ver Documento Completo
                                                    </Button>
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        onClick={() => handleReprocess(detail.id)}
                                                        className="border-white/[0.1] text-slate-300 hover:bg-white/[0.04]"
                                                    >
                                                        <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                                                        Reprocessar
                                                    </Button>
                                                </div>
                                            </div>

                                            {/* Extracted data */}
                                            <div>
                                                <h4 className="mb-3 text-sm font-medium text-slate-300">
                                                    Dados Extraídos
                                                </h4>
                                                {/* Fields */}
                                                {detail.fields && detail.fields.length > 0 && (
                                                    <div className="mb-4 space-y-2">
                                                        {detail.fields.map((field, i) => (
                                                            <div
                                                                key={i}
                                                                className="flex items-center justify-between rounded-lg bg-white/[0.03] px-3 py-2"
                                                            >
                                                                <span className="text-sm text-slate-400">
                                                                    {field.field_key}
                                                                </span>
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-sm font-medium text-slate-200">
                                                                        {field.field_value}
                                                                    </span>
                                                                    <span className="text-xs text-slate-600">
                                                                        {Math.round(field.confidence * 100)}%
                                                                    </span>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}

                                                {/* Tables */}
                                                {detail.tables &&
                                                    detail.tables.map((table, tIdx) => (
                                                        <div
                                                            key={tIdx}
                                                            className="mt-4 overflow-x-auto rounded-lg border border-white/[0.06]"
                                                        >
                                                            <table className="w-full text-sm">
                                                                <thead>
                                                                    <tr className="border-b border-white/[0.06] bg-white/[0.03]">
                                                                        {table.headers.map((h, i) => (
                                                                            <th
                                                                                key={i}
                                                                                className="px-3 py-2 text-left text-xs font-medium text-slate-400"
                                                                            >
                                                                                {h}
                                                                            </th>
                                                                        ))}
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {table.rows.map((row, rIdx) => (
                                                                        <tr
                                                                            key={rIdx}
                                                                            className="border-b border-white/[0.04] last:border-0"
                                                                        >
                                                                            {row.map((cell, cIdx) => (
                                                                                <td
                                                                                    key={cIdx}
                                                                                    className="px-3 py-2 text-slate-300"
                                                                                >
                                                                                    {cell}
                                                                                </td>
                                                                            ))}
                                                                        </tr>
                                                                    ))}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    ))}

                                                {detail.error_message && (
                                                    <div className="mt-4 rounded-lg bg-red-500/10 p-3 text-sm text-red-400">
                                                        {detail.error_message}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ) : null}
                                </div>
                            )}
                        </div>
                    ))}

                {/* Empty state */}
                {!loading && documents.length === 0 && (
                    <div className="py-12 text-center">
                        <FileText className="mx-auto h-10 w-10 text-slate-600" />
                        <p className="mt-3 text-sm text-slate-500">
                            Nenhum documento encontrado
                        </p>
                    </div>
                )}
            </div>

            {/* Pagination */}
            {
                totalPages > 1 && (
                    <div className="mt-4 flex items-center justify-between">
                        <span className="text-sm text-slate-500">
                            Página {page} de {totalPages}
                        </span>
                        <div className="flex gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                disabled={page <= 1}
                                onClick={() => setPage(page - 1)}
                                className="border-white/[0.1] text-slate-300 hover:bg-white/[0.04]"
                            >
                                <ChevronLeft className="mr-1 h-4 w-4" />
                                Anterior
                            </Button>
                            <Button
                                variant="outline"
                                size="sm"
                                disabled={page >= totalPages}
                                onClick={() => setPage(page + 1)}
                                className="border-white/[0.1] text-slate-300 hover:bg-white/[0.04]"
                            >
                                Próxima
                                <ChevronRight className="ml-1 h-4 w-4" />
                            </Button>
                        </div>
                    </div>
                )
            }
        </div >
    );
}
