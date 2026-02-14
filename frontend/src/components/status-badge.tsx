import { Badge } from "@/components/ui/badge";
import type { DocumentStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const statusConfig: Record<
    DocumentStatus,
    { label: string; className: string }
> = {
    processed: {
        label: "Concluído",
        className: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
    },
    processing: {
        label: "Processando",
        className: "bg-amber-500/15 text-amber-400 border-amber-500/20",
    },
    uploaded: {
        label: "Enviado",
        className: "bg-slate-500/15 text-slate-400 border-slate-500/20",
    },
    failed: {
        label: "Falhou",
        className: "bg-red-500/15 text-red-400 border-red-500/20",
    },
};

interface StatusBadgeProps {
    status: DocumentStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
    const config = statusConfig[status] || statusConfig.uploaded;
    return (
        <Badge
            variant="outline"
            className={cn("text-xs font-medium", config.className)}
        >
            {config.label}
        </Badge>
    );
}
