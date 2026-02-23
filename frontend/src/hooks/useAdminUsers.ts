import { useState, useCallback, useEffect } from "react";
import { userService } from "@/services/userService";
import { toast } from "sonner";
import type { User, CreateUserRequest, UpdateUserRequest } from "@/types";

export interface UserFormData {
  name: string;
  email: string;
  password: string;
  role: "admin" | "user";
}

export function useAdminUsers() {
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
      const res = await userService.getUsers();
      setUsers(res.users);
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
        await userService.updateUser(editingUser.id, payload);
        toast.success("Usuário atualizado com sucesso");
      } else {
        const payload: CreateUserRequest = {
          name: formData.name,
          email: formData.email,
          password: formData.password,
          role: formData.role,
        };
        await userService.createUser(payload);
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
      await userService.deleteUser(deletingUser.id);
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

  return {
    users,
    loading,
    dialogOpen,
    setDialogOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    editingUser,
    deletingUser,
    saving,
    formData,
    setFormData,
    openCreate,
    openEdit,
    openDelete,
    handleSave,
    handleDelete,
  };
}
