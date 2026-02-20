import { useState } from "react";
import {
    ColumnDef,
    flexRender,
    getCoreRowModel,
    getPaginationRowModel,
    useReactTable,
} from "@tanstack/react-table";

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Download, ChevronLeft, ChevronRight, FileText } from "lucide-react";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";

interface ChatDataTableProps {
    data: Record<string, unknown>[];
    onExport: (data: Record<string, unknown>[], filename?: string) => void;
}

export function ChatDataTable({ data, onExport }: ChatDataTableProps) {
    const [pagination, setPagination] = useState({
        pageIndex: 0, // initial page index
        pageSize: 5, // default page size
    });

    if (!data || data.length === 0) return null;

    const isSingleItem = data.length === 1;

    // Single Item View (Card)
    if (isSingleItem) {
        const item = data[0];
        return (
            <Card className="mt-4 bg-black/20 border-white/[0.08] overflow-hidden">
                <CardHeader className="flex flex-row items-center justify-between pb-2 bg-white/5 border-b border-white/[0.08] px-4 py-3">
                    <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-primary" />
                        <CardTitle className="text-sm font-medium text-foreground/90">
                            Detalhes do Registro
                        </CardTitle>
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onExport(data, `detalhes-${Date.now()}.csv`)}
                        className="h-7 text-xs gap-1.5 hover:bg-white/10"
                    >
                        <Download className="h-3.5 w-3.5" />
                        Exportar CSV
                    </Button>
                </CardHeader>
                <CardContent className="p-0">
                    <ScrollArea className="max-h-[400px]">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-white/[0.02]">
                            {Object.entries(item).map(([key, value]) => (
                                <div key={key} className="flex flex-col bg-transparent px-4 py-3 hover:bg-white/[0.02] transition-colors">
                                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                                        {key}
                                    </span>
                                    <span className="text-sm text-foreground/90 break-words">
                                        {String(value)}
                                    </span>
                                </div>
                            ))}
                        </div>
                        <ScrollBar orientation="vertical" />
                    </ScrollArea>
                </CardContent>
            </Card>
        );
    }

    // Multiple Items View (Table)
    const columns: ColumnDef<Record<string, unknown>>[] = Object.keys(data[0]).map(
        (key) => ({
            accessorKey: key,
            header: key,
            cell: ({ row }) => {
                const val = row.getValue(key);
                return <div className="min-w-[120px] max-w-[300px] truncate" title={String(val)}>{String(val)}</div>;
            },
        })
    );

    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        onPaginationChange: setPagination,
        state: {
            pagination,
        },
    });

    return (
        <div className="mt-4 overflow-hidden rounded-xl border border-white/[0.08] bg-black/20 shadow-sm">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between px-4 py-3 bg-white/5 border-b border-white/[0.08] gap-2 sm:gap-0">
                <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-primary" />
                    <span className="text-xs font-medium text-foreground/80 uppercase tracking-wider">
                        {data.length} Resultados Encontrados
                    </span>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onExport(data, `smartdocs-export-${Date.now()}.csv`)}
                    className="h-8 text-xs gap-1.5 bg-transparent border-white/10 hover:bg-white/10 hover:text-foreground transition-colors"
                >
                    <Download className="h-3.5 w-3.5" />
                    Exportar CSV
                </Button>
            </div>

            <ScrollArea className="w-full max-w-full rounded-b-lg">
                <Table>
                    <TableHeader className="bg-transparent pointer-events-none">
                        {table.getHeaderGroups().map((headerGroup) => (
                            <TableRow key={headerGroup.id} className="border-white/5 hover:bg-transparent">
                                {headerGroup.headers.map((header) => (
                                    <TableHead key={header.id} className="whitespace-nowrap px-4 text-xs font-medium text-muted-foreground uppercase tracking-wider h-10 align-middle">
                                        {header.isPlaceholder
                                            ? null
                                            : flexRender(
                                                header.column.columnDef.header,
                                                header.getContext()
                                            )}
                                    </TableHead>
                                ))}
                            </TableRow>
                        ))}
                    </TableHeader>
                    <TableBody>
                        {table.getRowModel().rows?.length ? (
                            table.getRowModel().rows.map((row) => (
                                <TableRow
                                    key={row.id}
                                    data-state={row.getIsSelected() && "selected"}
                                    className="border-white/5 hover:bg-white/[0.02] transition-colors"
                                >
                                    {row.getVisibleCells().map((cell) => (
                                        <TableCell key={cell.id} className="px-4 py-3 text-sm text-foreground/80 align-middle">
                                            {flexRender(
                                                cell.column.columnDef.cell,
                                                cell.getContext()
                                            )}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell
                                    colSpan={columns.length}
                                    className="h-24 text-center text-muted-foreground"
                                >
                                    Nenhum resultado.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
                <ScrollBar orientation="horizontal" />
            </ScrollArea>

            {/* Pagination Controls */}
            {data.length > pagination.pageSize && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-white/[0.08] bg-white/[0.01]">
                    <div className="flex-1 text-xs text-muted-foreground">
                        Mostrando {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1} a {Math.min((table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize, data.length)} de {data.length}
                    </div>
                    <div className="flex items-center space-x-2">
                        <Button
                            variant="outline"
                            size="icon"
                            className="h-7 w-7 bg-transparent border-white/10 hover:bg-white/10"
                            onClick={() => table.previousPage()}
                            disabled={!table.getCanPreviousPage()}
                        >
                            <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="outline"
                            size="icon"
                            className="h-7 w-7 bg-transparent border-white/10 hover:bg-white/10"
                            onClick={() => table.nextPage()}
                            disabled={!table.getCanNextPage()}
                        >
                            <ChevronRight className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
