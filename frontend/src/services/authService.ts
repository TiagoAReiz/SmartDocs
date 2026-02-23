import api from "@/lib/api";
import type { LoginRequest, LoginResponse, User } from "@/types";

export const authService = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const res = await api.post<LoginResponse>("/auth/login", credentials);
    return res.data;
  },
  getCurrentUser: async (): Promise<User> => {
    const res = await api.get<User>("/auth/me");
    return res.data;
  }
};
