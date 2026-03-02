'use client';

import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

import { Button } from '@/components/ui/button';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import { AuditLog, ActionType } from '@/types/auditLog';
import { auditService } from '@/services/auditService';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';

// Helper component for JSON display
const JsonDisplay = ({ data }: { data: Record<string, any> | null }) => {
    if (!data) return <span className="text-muted-foreground">-</span>;
    return (
        <pre className="text-xs bg-muted p-2 rounded-md overflow-x-auto max-w-[300px] max-h-[150px] overflow-y-auto">
            {JSON.stringify(data, null, 2)}
        </pre>
    );
};

export default function AuditLogsPage() {
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [loading, setLoading] = useState(true);

    // Pagination API state
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const limit = 20;

    // Filters state
    const [emailFilter, setEmailFilter] = useState('');
    const [actionFilter, setActionFilter] = useState<string>('ALL');
    const [entityFilter, setEntityFilter] = useState<string>('ALL');

    // Sorting state
    const [sortBy, setSortBy] = useState<'created_at' | 'user_email'>('created_at');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

    // Dialog state
    const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

    const fetchLogs = async () => {
        try {
            setLoading(true);
            const response = await auditService.getLogs({
                page,
                limit,
                email: emailFilter || undefined,
                action_type: actionFilter !== 'ALL' ? actionFilter : undefined,
                entity_type: entityFilter !== 'ALL' ? entityFilter : undefined,
                sort_by: sortBy,
                sort_order: sortOrder,
            });

            setLogs(response.data);
            setTotalPages(response.total_pages || 1);
            setTotalItems(response.total || 0);
        } catch (error: unknown) {
            const errorMessage = error instanceof Error ? error.message : 'Ocorreu um erro inesperado';
            toast.error('Erro ao carregar logs', {
                description: errorMessage,
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [page, sortBy, sortOrder]); // Re-fetch on pagination or sort change

    // Apply filters textually
    const handleApplyFilters = () => {
        setPage(1);
        fetchLogs();
    };

    const handleClearFilters = () => {
        setEmailFilter('');
        setActionFilter('ALL');
        setEntityFilter('ALL');
        setPage(1);
        // Since state updates are async, we can just call fetchLogs inside a timeout or let useEffect handle it if we add filters to dependency (but we don't want to fetch on every keystroke)
        setTimeout(() => {
            fetchLogs();
        }, 0);
    };

    const getActionBadgeColor = (action: ActionType) => {
        switch (action) {
            case 'CREATE': return 'bg-green-100 text-green-800 border-green-200';
            case 'UPDATE': return 'bg-blue-100 text-blue-800 border-blue-200';
            case 'DELETE': return 'bg-red-100 text-red-800 border-red-200';
            case 'PROCESS': return 'bg-purple-100 text-purple-800 border-purple-200';
            default: return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const toggleSort = (col: 'created_at' | 'user_email') => {
        if (sortBy === col) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(col);
            setSortOrder('desc');
        }
        setPage(1);
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Logs de Auditoria</h1>
                <p className="text-muted-foreground mt-2">
                    Visualize o histórico de ações no sistema. ({totalItems} registros totais)
                </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 items-end bg-card p-4 rounded-lg border">
                <div className="space-y-2 flex-grow max-w-sm">
                    <label className="text-sm font-medium">Email do Usuário</label>
                    <Input
                        placeholder="Buscar por email..."
                        value={emailFilter}
                        onChange={(e) => setEmailFilter(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleApplyFilters()}
                    />
                </div>

                <div className="space-y-2 w-48">
                    <label className="text-sm font-medium">Ação</label>
                    <Select value={actionFilter} onValueChange={setActionFilter}>
                        <SelectTrigger>
                            <SelectValue placeholder="Todas" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">Todas</SelectItem>
                            <SelectItem value="CREATE">Criar</SelectItem>
                            <SelectItem value="UPDATE">Atualizar</SelectItem>
                            <SelectItem value="DELETE">Deletar</SelectItem>
                            <SelectItem value="PROCESS">Processos</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2 w-48">
                    <label className="text-sm font-medium">Entidade</label>
                    <Select value={entityFilter} onValueChange={setEntityFilter}>
                        <SelectTrigger>
                            <SelectValue placeholder="Todas" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">Todas</SelectItem>
                            <SelectItem value="USER">Usuário</SelectItem>
                            <SelectItem value="DOCUMENT">Documento</SelectItem>
                            <SelectItem value="CHAT_THREAD">Chat Thread</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="flex gap-2">
                    <Button onClick={handleApplyFilters} disabled={loading}>
                        Filtrar
                    </Button>
                    <Button variant="outline" onClick={handleClearFilters} disabled={loading}>
                        Limpar
                    </Button>
                </div>
            </div>

            <div className="rounded-md border bg-card">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead
                                className="cursor-pointer hover:bg-muted/50 transition-colors w-[200px]"
                                onClick={() => toggleSort('created_at')}
                            >
                                Data/Hora {sortBy === 'created_at' && (sortOrder === 'asc' ? '↑' : '↓')}
                            </TableHead>
                            <TableHead
                                className="cursor-pointer hover:bg-muted/50 transition-colors hidden md:table-cell"
                                onClick={() => toggleSort('user_email')}
                            >
                                Usuário {sortBy === 'user_email' && (sortOrder === 'asc' ? '↑' : '↓')}
                            </TableHead>
                            <TableHead>Ação</TableHead>
                            <TableHead>Entidade</TableHead>
                            <TableHead className="text-right">Detalhes</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {loading ? (
                            <TableRow>
                                <TableCell colSpan={5} className="text-center h-24 text-muted-foreground">
                                    Carregando logs de auditoria...
                                </TableCell>
                            </TableRow>
                        ) : logs.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={5} className="text-center h-24 text-muted-foreground">
                                    Nenhum registro encontrado.
                                </TableCell>
                            </TableRow>
                        ) : (
                            logs.map((log) => (
                                <TableRow key={log.id}>
                                    <TableCell className="whitespace-nowrap">
                                        {format(new Date(log.created_at), "dd/MM/yyyy HH:mm:ss", { locale: ptBR })}
                                    </TableCell>
                                    <TableCell className="font-medium hidden md:table-cell">
                                        {log.user_email}
                                    </TableCell>
                                    <TableCell>
                                        <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getActionBadgeColor(log.action_type)}`}>
                                            {log.action_type}
                                        </span>
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex flex-col">
                                            <span className="font-medium text-sm">{log.entity_type}</span>
                                            <span className="text-xs text-muted-foreground font-mono truncate max-w-[150px]" title={log.entity_id}>
                                                {log.entity_id}
                                            </span>
                                        </div>
                                    </TableCell>
                                    <TableCell className="text-right">
                                        <Button variant="ghost" size="sm" onClick={() => setSelectedLog(log)}>
                                            Ver Dados
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>

            {totalPages > 1 && (
                <div className="flex justify-between items-center mt-4">
                    <div className="text-sm text-muted-foreground">
                        Página {page} de {totalPages}
                    </div>
                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1 || loading}
                        >
                            Anterior
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page === totalPages || loading}
                        >
                            Próxima
                        </Button>
                    </div>
                </div>
            )}

            {/* Details Dialog */}
            <Dialog open={!!selectedLog} onOpenChange={(open) => !open && setSelectedLog(null)}>
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>Detalhes da Auditoria</DialogTitle>
                    </DialogHeader>

                    {selectedLog && (
                        <div className="space-y-4 mt-4">
                            <div className="grid grid-cols-2 gap-4 bg-muted/30 p-4 rounded-lg text-sm">
                                <div>
                                    <span className="text-muted-foreground block text-xs">Ação</span>
                                    <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium border ${getActionBadgeColor(selectedLog.action_type)}`}>
                                        {selectedLog.action_type}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-muted-foreground block text-xs">Data/Hora</span>
                                    <span className="font-medium">{format(new Date(selectedLog.created_at), "dd/MM/yyyy HH:mm:ss", { locale: ptBR })}</span>
                                </div>
                                <div>
                                    <span className="text-muted-foreground block text-xs">Usuário responsável</span>
                                    <span className="font-medium break-all">{selectedLog.user_email}</span>
                                </div>
                                <div>
                                    <span className="text-muted-foreground block text-xs">Entidade</span>
                                    <span className="font-medium">{selectedLog.entity_type}</span>
                                </div>
                                <div className="col-span-2">
                                    <span className="text-muted-foreground block text-xs">ID da Entidade</span>
                                    <span className="font-mono text-xs break-all bg-muted px-1.5 py-0.5 rounded">{selectedLog.entity_id}</span>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border-t pt-4">
                                <div className="space-y-2">
                                    <h4 className="text-sm font-medium flex items-center justify-between">
                                        Valores Antigos
                                        <span className="text-xs text-muted-foreground font-normal bg-muted px-1.5 rounded">old_values</span>
                                    </h4>
                                    <JsonDisplay data={selectedLog.old_values} />
                                </div>

                                <div className="space-y-2">
                                    <h4 className="text-sm font-medium flex items-center justify-between">
                                        Novos Valores
                                        <span className="text-xs text-muted-foreground font-normal bg-muted px-1.5 rounded">new_values</span>
                                    </h4>
                                    <JsonDisplay data={selectedLog.new_values} />
                                </div>
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
