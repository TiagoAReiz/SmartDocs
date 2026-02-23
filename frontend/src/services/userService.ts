import api from "@/lib/api";
import type { User, CreateUserRequest, UpdateUserRequest } from "@/types";

export const userService = {
  getUsers: async (): Promise<{ users: User[] }> => {
    const res = await api.get<{ users: User[] }>("/admin/users");
    return res.data;
  },
  createUser: async (payload: CreateUserRequest): Promise<void> => {
    await api.post("/admin/users", payload);
  },
  updateUser: async (id: number, payload: UpdateUserRequest): Promise<void> => {
    await api.put(`/admin/users/${id}`, payload);
  },
  deleteUser: async (id: number): Promise<void> => {
    await api.delete(`/admin/users/${id}`);
  }
};
