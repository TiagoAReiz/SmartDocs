import { useState, useEffect } from "react";
import useSWR from "swr";
import { documentService } from "@/services/documentService";
import { toast } from "sonner";
import type { DocumentDetail, PaginatedDocuments } from "@/types";

export function useDocuments() {
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

  const fetcher = async () => {
    return documentService.getDocuments(params);
  };

  const { data, mutate, isLoading } = useSWR<PaginatedDocuments>(
    `/documents?${params.toString()}`,
    fetcher,
    {
      refreshInterval: (currentData) => {
        if (!currentData) return 0;
        const needsPolling = currentData.documents.some(
          (d) => d.status === "uploaded" || d.status === "processing"
        );
        return needsPolling ? 3000 : 0;
      },
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
      const res = await documentService.getDocument(docId);
      setDetail(res);

      if (res.mime_type === "application/pdf" || res.mime_type?.startsWith("image/")) {
        const fileRes = await documentService.downloadFile(docId);
        const url = URL.createObjectURL(fileRes);
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
      const fileBlob = await documentService.downloadFile(doc.id);
      const url = window.URL.createObjectURL(new Blob([fileBlob], { type: doc.mime_type }));
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
      await documentService.reprocess(docId);
      toast.success("Reprocessamento iniciado");
      mutate();
    } catch {
      toast.error("Erro ao reprocessar documento");
    }
  };

  const handleDelete = async (docId: number) => {
    try {
      await documentService.deleteDocument(docId);
      toast.success("Documento removido com sucesso");
      mutate();
    } catch {
      toast.error("Erro ao remover documento");
    }
  };

  return {
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
  };
}
