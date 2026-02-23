import { useState, useCallback, useEffect } from "react";
import { documentService } from "@/services/documentService";
import { toast } from "sonner";
import type { DocumentStatus } from "@/types";

export interface UploadItem {
  id: string;
  file: File;
  progress: number;
  status: DocumentStatus;
  documentId?: number;
}

export function useDocumentUpload() {
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const acceptedTypes = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "image/jpeg",
    "image/png",
  ];

  const handleFiles = useCallback(async (files: FileList | File[]) => {
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

    try {
      const progressInterval = setInterval(() => {
        setUploads((prev) =>
          prev.map((item) =>
            newItems.find((n) => n.id === item.id) && item.progress < 90
              ? { ...item, progress: item.progress + 10 }
              : item
          )
        );
      }, 200);

      const res = await documentService.uploadFiles(fileArray);

      clearInterval(progressInterval);

      setUploads((prev) =>
        prev.map((item) => {
          const newItem = newItems.find((n) => n.id === item.id);
          if (newItem) {
            const idx = newItems.indexOf(newItem);
            const doc = res.documents[idx];
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

      toast.success(`${fileArray.length} arquivo(s) enviado(s) com sucesso!`);
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
  }, [acceptedTypes]);

  useEffect(() => {
    const processingItems = uploads.filter(
      (u) => u.status === "processing" || u.status === "uploaded"
    );
    if (processingItems.length === 0) return;

    const interval = setInterval(async () => {
      for (const item of processingItems) {
        if (!item.documentId) continue;
        try {
          const res = await documentService.checkStatus(item.documentId);
          const newStatus = res.status.toLowerCase() as DocumentStatus;
          if (newStatus !== item.status) {
            setUploads((prev) =>
              prev.map((u) => (u.id === item.id ? { ...u, status: newStatus } : u))
            );
          }
        } catch {
          // Ignore errors during polling
        }
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [uploads]);

  const handleReprocess = async (item: UploadItem) => {
    if (!item.documentId) return;
    try {
      await documentService.reprocess(item.documentId);
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

  return {
    uploads,
    isUploading,
    handleFiles,
    handleReprocess,
  };
}
