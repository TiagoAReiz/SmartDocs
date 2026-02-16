"use client";

import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import type { User, CreateUserRequest, UpdateUserRequest } from "@/lib/types";
import { AuthGuard } from "@/components/auth-guard";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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
import {
    UserPlus,
    Pencil,
    Trash2,
    Loader2,
    AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";

interface UserFormData {
    name: string;
    email: string;
    password: string;
    role: "admin" | "user";
}

export default function AdminUsersPage() {
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [deletingUser, setDeletingUser] = useState<User | null>(null);
    const [saving, setSaving] = useState(false);
    const [formData, setFormData] = useState<UserFormData>({
        name: "",
        email: "",
        password: "",
        role: "user",
    });

    const fetchUsers = useCallback(async () => {
        try {
            const res = await api.get<{ users: User[] }>("/admin/users");
            setUsers(res.data.users);
        } catch {
            toast.error("Erro ao carregar usuários");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUsers();
    }, [fetchUsers]);

    const openCreate = () => {
        setEditingUser(null);
        setFormData({ name: "", email: "", password: "", role: "user" });
        setDialogOpen(true);
    };

    const openEdit = (user: User) => {
        setEditingUser(user);
        setFormData({ name: user.name, email: user.email, password: "", role: user.role });
        setDialogOpen(true);
    };

    const openDelete = (user: User) => {
        setDeletingUser(user);
        setDeleteDialogOpen(true);
    };

    const handleSave = async () => {
        if (!formData.name || !formData.email) {
            toast.error("Preencha todos os campos obrigatórios");
            return;
        }
        if (!editingUser && !formData.password) {
            toast.error("Senha é obrigatória para novos usuários");
            return;
        }

        setSaving(true);
        try {
            if (editingUser) {
                const payload: UpdateUserRequest = {
                    name: formData.name,
                    email: formData.email,
                    role: formData.role,
                    password: formData.password || null,
                };
                await api.put(`/admin/users/${editingUser.id}`, payload);
                toast.success("Usuário atualizado com sucesso");
            } else {
                const payload: CreateUserRequest = {
                    name: formData.name,
                    email: formData.email,
                    password: formData.password,
                    role: formData.role,
                };
                await api.post("/admin/users", payload);
                toast.success("Usuário criado com sucesso");
            }
            setDialogOpen(false);
            fetchUsers();
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } };
            toast.error(error.response?.data?.detail || "Erro ao salvar usuário");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!deletingUser) return;
        setSaving(true);
        try {
            await api.delete(`/admin/users/${deletingUser.id}`);
            toast.success("Usuário removido com sucesso");
            setDeleteDialogOpen(false);
            setDeletingUser(null);
            fetchUsers();
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } };
            toast.error(error.response?.data?.detail || "Erro ao remover usuário");
        } finally {
            setSaving(false);
        }
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
        });
    };

    return (
        <AuthGuard adminOnly>
            <div>
                <PageHeader
                    title="Administração de Usuários"
                    subtitle="Gerencie os usuários do sistema"
                    actions={
                        <Button
                            onClick={openCreate}
                            className="bg-[#136dec] text-white shadow-lg shadow-[#136dec]/20 hover:bg-[#1178ff]"
                        >
                            <UserPlus className="mr-2 h-4 w-4" />
                            Novo Usuário
                        </Button>
                    }
                />

                {/* Users table */}
                <Card className="mt-6 overflow-hidden border-white/[0.06] bg-transparent">
                    <div className="overflow-x-auto">
                        <div className="min-w-[800px]">
                            {/* Header */}
                            <div className="grid grid-cols-[1fr_200px_100px_140px_100px] gap-4 border-b border-white/[0.06] bg-[#1E293B]/80 px-4 py-3 text-xs font-medium uppercase tracking-wider text-slate-500">
                                <span>Nome</span>
                                <span>Email</span>
                                <span>Perfil</span>
                                <span>Data Cadastro</span>
                                <span>Ações</span>
                            </div>

                            {/* Loading */}
                            {loading &&
                                Array.from({ length: 4 }).map((_, i) => (
                                    <div
                                        key={i}
                                        className="grid grid-cols-[1fr_200px_100px_140px_100px] gap-4 border-b border-white/[0.04] px-4 py-4"
                                    >
                                        <div className="h-4 w-32 animate-pulse rounded bg-white/[0.06]" />
                                        <div className="h-4 w-40 animate-pulse rounded bg-white/[0.06]" />
                                        <div className="h-5 w-16 animate-pulse rounded bg-white/[0.06]" />
                                        <div className="h-4 w-24 animate-pulse rounded bg-white/[0.06]" />
                                        <div className="h-4 w-16 animate-pulse rounded bg-white/[0.06]" />
                                    </div>
                                ))}

                            {/* Rows */}
                            {!loading &&
                                users.map((user) => (
                                    <div
                                        key={user.id}
                                        className="grid grid-cols-[1fr_200px_100px_140px_100px] items-center gap-4 border-b border-white/[0.04] px-4 py-4 transition-colors hover:bg-white/[0.02]"
                                    >
                                        <span className="text-sm font-medium text-slate-200">
                                            {user.name}
                                        </span>
                                        <div className="truncate text-sm text-slate-400" title={user.email}>
                                            {user.email}
                                        </div>
                                        <Badge
                                            variant="outline"
                                            className={`text-xs w-fit ${user.role === "admin"
                                                ? "bg-[#136dec]/15 text-[#136dec] border-[#136dec]/20"
                                                : "bg-slate-500/15 text-slate-400 border-slate-500/20"
                                                }`}
                                        >
                                            {user.role === "admin" ? "Admin" : "Usuário"}
                                        </Badge>
                                        <span className="text-sm text-slate-400">
                                            {user.created_at ? formatDate(user.created_at) : "—"}
                                        </span>
                                        <div className="flex gap-1">
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => openEdit(user)}
                                                className="h-8 w-8 text-slate-400 hover:text-[#136dec]"
                                            >
                                                <Pencil className="h-3.5 w-3.5" />
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => openDelete(user)}
                                                className="h-8 w-8 text-slate-400 hover:text-red-400"
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </Button>
                                        </div>
                                    </div>
                                ))}

                            {!loading && users.length === 0 && (
                                <div className="py-12 text-center text-sm text-slate-500">
                                    Nenhum usuário cadastrado
                                </div>
                            )}
                        </div>
                    </div>
                </Card>

                {/* Create/Edit Dialog */}
                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                    <DialogContent className="border-white/[0.08] bg-[#1E293B] text-slate-200 sm:max-w-md">
                        <DialogHeader>
                            <DialogTitle className="text-white">
                                {editingUser ? "Editar Usuário" : "Novo Usuário"}
                            </DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label className="text-slate-300">Nome</Label>
                                <Input
                                    value={formData.name}
                                    onChange={(e) =>
                                        setFormData({ ...formData, name: e.target.value })
                                    }
                                    className="border-white/[0.08] bg-white/[0.04] text-slate-200"
                                    placeholder="Nome completo"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-slate-300">Email</Label>
                                <Input
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) =>
                                        setFormData({ ...formData, email: e.target.value })
                                    }
                                    className="border-white/[0.08] bg-white/[0.04] text-slate-200"
                                    placeholder="email@empresa.com"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-slate-300">
                                    Senha{editingUser ? " (deixe vazio para manter)" : ""}
                                </Label>
                                <Input
                                    type="password"
                                    value={formData.password}
                                    onChange={(e) =>
                                        setFormData({ ...formData, password: e.target.value })
                                    }
                                    className="border-white/[0.08] bg-white/[0.04] text-slate-200"
                                    placeholder="••••••••"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-slate-300">Perfil</Label>
                                <Select
                                    value={formData.role}
                                    onValueChange={(val) =>
                                        setFormData({
                                            ...formData,
                                            role: val as "admin" | "user",
                                        })
                                    }
                                >
                                    <SelectTrigger className="border-white/[0.08] bg-white/[0.04] text-slate-200">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent className="border-white/[0.08] bg-[#1E293B]">
                                        <SelectItem value="user">Usuário</SelectItem>
                                        <SelectItem value="admin">Admin</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <DialogFooter>
                            <Button
                                variant="outline"
                                onClick={() => setDialogOpen(false)}
                                className="border-white/[0.1] text-slate-300 hover:bg-white/[0.04]"
                            >
                                Cancelar
                            </Button>
                            <Button
                                onClick={handleSave}
                                disabled={saving}
                                className="bg-[#136dec] text-white hover:bg-[#1178ff]"
                            >
                                {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                {editingUser ? "Salvar" : "Criar"}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>

                {/* Delete confirmation */}
                <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                    <DialogContent className="border-white/[0.08] bg-[#1E293B] text-slate-200 sm:max-w-sm">
                        <DialogHeader>
                            <DialogTitle className="flex items-center gap-2 text-white">
                                <AlertTriangle className="h-5 w-5 text-red-400" />
                                Confirmar Exclusão
                            </DialogTitle>
                        </DialogHeader>
                        <p className="text-sm text-slate-400">
                            Tem certeza que deseja remover o usuário{" "}
                            <span className="font-medium text-slate-200">
                                {deletingUser?.name}
                            </span>
                            ? Esta ação não pode ser desfeita.
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
                                onClick={handleDelete}
                                disabled={saving}
                                className="bg-red-600 text-white hover:bg-red-700"
                            >
                                {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Remover
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>
        </AuthGuard>
    );
}
