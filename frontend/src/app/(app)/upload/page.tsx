"use client";

import { useState, useRef, useCallback } from "react";
import api from "@/lib/api";
import type { UploadResponse } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { StatusBadge } from "@/components/status-badge";
import {
    CloudUpload,
    FileUp,
    CheckCircle2,
    XCircle,
    RefreshCw,
    Loader2,
    File,
    FileText,
    Image as ImageIcon,
    FileSpreadsheet,
    FileWarning
} from "lucide-react";
import { toast } from "sonner";
import type { DocumentStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

interface UploadItem {
    id: string;
    file: File;
    progress: number;
    status: DocumentStatus;
    documentId?: number;
}

export default function UploadPage() {
    const [uploads, setUploads] = useState<UploadItem[]>([]);
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const acceptedTypes = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "image/jpeg",
        "image/png",
    ];

    const acceptedExtensions = ".pdf,.docx,.xlsx,.pptx,.jpg,.jpeg,.png";

    const handleFiles = useCallback(
        async (files: FileList | File[]) => {
            const fileArray = Array.from(files).filter(
                (f) =>
                    acceptedTypes.includes(f.type) ||
                    /\.(pdf|docx|xlsx|pptx|jpe?g|png)$/i.test(f.name)
            );

            if (fileArray.length === 0) {
                toast.error("Nenhum arquivo com formato suportado foi selecionado");
                return;
            }

            const newItems: UploadItem[] = fileArray.map((file) => ({
                id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
                file,
                progress: 0,
                status: "uploaded" as DocumentStatus,
            }));

            setUploads((prev) => [...newItems, ...prev]);
            setIsUploading(true);

            const formData = new FormData();
            fileArray.forEach((file) => formData.append("files", file));

            try {
                // Simulate progress
                const progressInterval = setInterval(() => {
                    setUploads((prev) =>
                        prev.map((item) =>
                            newItems.find((n) => n.id === item.id) && item.progress < 90
                                ? { ...item, progress: item.progress + 10 }
                                : item
                        )
                    );
                }, 200);

                const res = await api.post<UploadResponse>(
                    "/documents/upload",
                    formData,
                    {
                        headers: { "Content-Type": "multipart/form-data" },
                    }
                );

                clearInterval(progressInterval);

                setUploads((prev) =>
                    prev.map((item) => {
                        const newItem = newItems.find((n) => n.id === item.id);
                        if (newItem) {
                            const idx = newItems.indexOf(newItem);
                            const doc = res.data.documents[idx];
                            return {
                                ...item,
                                progress: 100,
                                status: "processing" as DocumentStatus,
                                documentId: doc?.id,
                            };
                        }
                        return item;
                    })
                );

                toast.success(
                    `${fileArray.length} arquivo(s) enviado(s) com sucesso!`
                );
            } catch {
                setUploads((prev) =>
                    prev.map((item) =>
                        newItems.find((n) => n.id === item.id)
                            ? { ...item, progress: 100, status: "failed" as DocumentStatus }
                            : item
                    )
                );
                toast.error("Erro ao fazer upload dos arquivos");
            } finally {
                setIsUploading(false);
            }
        },
        [acceptedTypes]
    );

    const handleReprocess = async (item: UploadItem) => {
        if (!item.documentId) return;
        try {
            await api.post(`/documents/${item.documentId}/reprocess`);
            setUploads((prev) =>
                prev.map((u) =>
                    u.id === item.id ? { ...u, status: "processing" as DocumentStatus } : u
                )
            );
            toast.success("Reprocessamento iniciado");
        } catch {
            toast.error("Erro ao reprocessar documento");
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => setIsDragging(false);

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        handleFiles(e.dataTransfer.files);
    };

    const formatSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / 1048576).toFixed(1)} MB`;
    };

    const getFileIcon = (filename: string) => {
        const ext = filename.split(".").pop()?.toLowerCase();
        if (["pdf"].includes(ext || "")) return <FileText className="h-6 w-6 text-red-400" />;
        if (["xls", "xlsx", "csv"].includes(ext || "")) return <FileSpreadsheet className="h-6 w-6 text-emerald-400" />;
        if (["jpg", "jpeg", "png"].includes(ext || "")) return <ImageIcon className="h-6 w-6 text-purple-400" />;
        return <File className="h-6 w-6 text-primary" />;
    };

    return (
        <div className="space-y-6">
            <PageHeader
                title="Upload"
                subtitle="Envie seus documentos para análise"
            />

            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                    "relative flex cursor-pointer flex-col items-center justify-center gap-4 rounded-3xl border-2 border-dashed p-12 transition-all duration-300 md:p-20",
                    isDragging
                        ? "border-primary bg-primary/10 scale-[1.01]"
                        : "border-white/10 bg-card/30 hover:border-primary/50 hover:bg-card/50"
                )}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept={acceptedExtensions}
                    onChange={(e) => e.target.files && handleFiles(e.target.files)}
                    className="hidden"
                />

                <div className={cn(
                    "flex h-20 w-20 items-center justify-center rounded-full bg-white/5 shadow-inner transition-transform duration-500",
                    isDragging ? "scale-110" : ""
                )}>
                    {isDragging ? (
                        <CloudUpload className="h-10 w-10 text-primary animate-bounce" />
                    ) : (
                        <FileUp className="h-10 w-10 text-muted-foreground" />
                    )}
                </div>

                <div className="text-center space-y-2">
                    <h3 className="text-xl font-medium text-foreground">
                        {isDragging ? "Solte para enviar" : "Arraste e solte seus arquivos"}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                        Ou clique para selecionar do computador
                    </p>
                </div>

                <div className="mt-4 flex flex-wrap justify-center gap-2">
                    {["PDF", "DOCX", "XLSX", "JPG", "PNG"].map((type) => (
                        <span key={type} className="rounded-md bg-white/5 px-2 py-1 text-[10px] font-medium text-muted-foreground">
                            {type}
                        </span>
                    ))}
                </div>
            </div>

            {/* Upload list */}
            {uploads.length > 0 && (
                <div className="space-y-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
                    <div className="flex items-center justify-between">
                        <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider">
                            Fila de Upload ({uploads.length})
                        </h2>
                        {isUploading && (
                            <div className="flex items-center gap-2 text-xs text-primary animate-pulse">
                                <Loader2 className="h-3 w-3 animate-spin" />
                                Processando...
                            </div>
                        )}
                    </div>

                    <div className="grid gap-3">
                        {uploads.map((item) => (
                            <div
                                key={item.id}
                                className="group relative overflow-hidden rounded-xl border border-white/[0.08] bg-card p-4 transition-all hover:bg-card/80"
                            >
                                <div className="flex items-start gap-4">
                                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-white/[0.03]">
                                        {getFileIcon(item.file.name)}
                                    </div>

                                    <div className="flex-1 min-w-0 space-y-3">
                                        <div className="flex items-start justify-between gap-4">
                                            <div>
                                                <p className="truncate font-medium text-foreground">
                                                    {item.file.name}
                                                </p>
                                                <p className="text-xs text-muted-foreground">
                                                    {formatSize(item.file.size)}
                                                </p>
                                            </div>
                                            <StatusBadge status={item.status} />
                                        </div>

                                        <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-white/5">
                                            <div
                                                className="absolute inset-y-0 left-0 bg-primary transition-all duration-300"
                                                style={{ width: `${item.progress}%` }}
                                            />
                                        </div>
                                    </div>

                                    {item.status === "failed" && (
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => handleReprocess(item)}
                                            className="h-8 w-8 text-muted-foreground hover:text-primary hover:bg-primary/10"
                                            title="Tentar novamente"
                                        >
                                            <RefreshCw className="h-4 w-4" />
                                        </Button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
