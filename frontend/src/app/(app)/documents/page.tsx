"use client";

import React, { Fragment } from "react";
import { useDocuments } from "@/hooks/useDocuments";
import type { DocumentDetail } from "@/types";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/contexts/auth-context";
import {
    Search,
    ChevronDown,
    FileText,
    RefreshCw,
    Loader2,
    ChevronLeft,
    ChevronRight,
    Download,
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function DocumentsPage() {
    const { isAdmin } = useAuth();
    const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
    const [documentToDelete, setDocumentToDelete] = React.useState<DocumentDetail | null>(null);
    const {
        documents,
        total,
        totalPages,
        loading,
        searchInput,
        setSearchInput,
        statusFilter,
        setStatusFilter,
        page,
        setPage,
        expandedId,
        detail,
        previewUrl,
        detailLoading,
        handleExpand,
        handleDownload,
        handleReprocess,
        handleDelete,
    } = useDocuments();

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
        });
    };

    const confirmDelete = (doc: DocumentDetail) => {
        setDocumentToDelete(doc);
        setDeleteDialogOpen(true);
    };

    const executeDelete = async () => {
        if (documentToDelete) {
            await handleDelete(documentToDelete.id);
            setDeleteDialogOpen(false);
            setDocumentToDelete(null);
        }
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
                                            onDelete={isAdmin ? () => detail && confirmDelete(detail) : undefined}
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
                                        <Fragment key={doc.id}>
                                            <tr
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
                                                                onDelete={isAdmin ? () => detail && confirmDelete(detail) : undefined}
                                                            />
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                        </Fragment>
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

            {/* Delete confirmation */}
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogContent className="border-white/[0.08] bg-[#1E293B] text-slate-200 sm:max-w-sm">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-white">
                            Confirmar Exclusão
                        </DialogTitle>
                    </DialogHeader>
                    <p className="text-sm text-slate-400">
                        Tem certeza que deseja remover o documento{" "}
                        <span className="font-medium text-slate-200">
                            {documentToDelete?.filename}
                        </span>
                        ? Esta ação não pode ser desfeita e removerá todos os dados extraídos.
                    </p>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setDeleteDialogOpen(false)}
                            className="border-white/[0.1] text-slate-300 hover:bg-white/[0.04]"
                        >
                            Cancelar
                        </Button>
                        <Button
                            onClick={executeDelete}
                            className="bg-red-600 text-white hover:bg-red-700"
                        >
                            Remover
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

// Extracted Component for Detail View to avoid duplication
function ExpandedDocumentDetail({
    detail,
    loading,
    previewUrl,
    onDownload,
    onReprocess,
    onDelete
}: {
    detail: DocumentDetail | null;
    loading: boolean;
    previewUrl: string | null;
    onDownload: () => void;
    onReprocess: () => void;
    onDelete?: () => void;
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
                        {onDelete && (
                            <Button variant="ghost" size="sm" onClick={onDelete} className="h-8 text-xs hover:bg-red-500/10 text-red-500">
                                Remover
                            </Button>
                        )}
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
