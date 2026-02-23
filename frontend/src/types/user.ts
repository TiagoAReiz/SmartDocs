export interface User {
  id: number;
  name: string;
  email: string;
  role: "admin" | "user";
  created_at?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface CreateUserRequest {
  name: string;
  email: string;
  password: string;
  role: "admin" | "user";
}

export interface UpdateUserRequest {
  name: string;
  email: string;
  role: "admin" | "user";
  password: string | null;
}
