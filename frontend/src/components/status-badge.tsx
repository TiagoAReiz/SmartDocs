import { Badge } from "@/components/ui/badge";
import type { DocumentStatus } from "@/lib/types";
import { cn } from "@/lib/utils";
import { CheckCircle2, Loader2, XCircle, Clock } from "lucide-react";

const statusConfig: Record<
    DocumentStatus,
    { label: string; className: string; icon: React.ReactNode }
> = {
    processed: {
        label: "Concluído",
        className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20",
        icon: <CheckCircle2 className="h-3 w-3 mr-1" />,
    },
    processing: {
        label: "Processando",
        className: "bg-amber-500/10 text-amber-400 border-amber-500/20 hover:bg-amber-500/20",
        icon: <Loader2 className="h-3 w-3 mr-1 animate-spin" />,
    },
    uploaded: {
        label: "Enviado",
        className: "bg-slate-500/10 text-slate-400 border-slate-500/20 hover:bg-slate-500/20",
        icon: <Clock className="h-3 w-3 mr-1" />,
    },
    failed: {
        label: "Falhou",
        className: "bg-red-500/10 text-red-500 border-red-500/20 hover:bg-red-500/20",
        icon: <XCircle className="h-3 w-3 mr-1" />,
    },
};

interface StatusBadgeProps {
    status: DocumentStatus;
    className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
    const config = statusConfig[status] || statusConfig.uploaded;
    return (
        <Badge
            variant="outline"
            className={cn(
                "flex items-center gap-0.5 rounded-full px-2.5 py-0.5 text-[10px] font-medium transition-colors uppercase tracking-wider",
                config.className,
                className
            )}
        >
            {config.icon}
            {config.label}
        </Badge>
    );
}
