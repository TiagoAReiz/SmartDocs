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
} from "lucide-react";
import { toast } from "sonner";
import type { DocumentStatus } from "@/lib/types";

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

                // Update items with response data
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

    const statusIcon = (status: DocumentStatus) => {
        switch (status) {
            case "processed":
                return <CheckCircle2 className="h-5 w-5 text-emerald-400" />;
            case "processing":
                return <Loader2 className="h-5 w-5 animate-spin text-amber-400" />;
            case "failed":
                return <XCircle className="h-5 w-5 text-red-400" />;
            default:
                return <FileUp className="h-5 w-5 text-slate-400" />;
        }
    };

    return (
        <div>
            <PageHeader
                title="Upload de Documentos"
                subtitle="Envie documentos para extração inteligente de dados"
            />

            {/* Dropzone */}
            <Card
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`mt-6 flex cursor-pointer flex-col items-center justify-center border-2 border-dashed p-12 transition-all duration-200 ${isDragging
                        ? "border-[#136dec] bg-[#136dec]/5"
                        : "border-white/[0.1] bg-[#1E293B]/50 hover:border-white/20 hover:bg-[#1E293B]/70"
                    }`}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept={acceptedExtensions}
                    onChange={(e) => e.target.files && handleFiles(e.target.files)}
                    className="hidden"
                />
                <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#136dec]/10">
                    <CloudUpload className="h-8 w-8 text-[#136dec]" />
                </div>
                <h3 className="text-lg font-medium text-slate-200">
                    {isDragging ? "Solte os arquivos aqui" : "Arraste arquivos ou clique para selecionar"}
                </h3>
                <p className="mt-2 text-sm text-slate-500">
                    Formatos aceitos: PDF, DOCX, XLSX, PPTX, JPG, PNG
                </p>
            </Card>

            {/* Upload list */}
            {uploads.length > 0 && (
                <div className="mt-8">
                    <h2 className="mb-4 text-lg font-medium text-slate-200">
                        Uploads Recentes
                    </h2>
                    <div className="space-y-3">
                        {uploads.map((item) => (
                            <Card
                                key={item.id}
                                className="flex items-center gap-4 border-white/[0.06] bg-[#1E293B]/60 p-4"
                            >
                                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/[0.04]">
                                    <File className="h-5 w-5 text-slate-400" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-3">
                                        <p className="truncate text-sm font-medium text-slate-200">
                                            {item.file.name}
                                        </p>
                                        <span className="shrink-0 text-xs text-slate-500">
                                            {formatSize(item.file.size)}
                                        </span>
                                    </div>
                                    {item.progress < 100 && (
                                        <Progress
                                            value={item.progress}
                                            className="mt-2 h-1.5 bg-white/[0.06] [&>div]:bg-[#136dec]"
                                        />
                                    )}
                                </div>
                                <div className="flex items-center gap-3">
                                    <StatusBadge status={item.status} />
                                    {statusIcon(item.status)}
                                    {item.status === "failed" && item.documentId && (
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => handleReprocess(item)}
                                            className="text-slate-400 hover:text-[#136dec]"
                                        >
                                            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                                            Reprocessar
                                        </Button>
                                    )}
                                </div>
                            </Card>
                        ))}
                    </div>
                </div>
            )}

            {isUploading && (
                <div className="mt-4 flex items-center gap-2 text-sm text-slate-400">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Enviando arquivos...
                </div>
            )}
        </div>
    );
}
