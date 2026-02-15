"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import type { User, LoginRequest, LoginResponse } from "@/lib/types";

interface AuthContextType {
    user: User | null;
    token: string | null;
    loading: boolean;
    isAdmin: boolean;
    login: (credentials: LoginRequest) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    const isAdmin = user?.role === "admin";

    const logout = useCallback(() => {
        setUser(null);
        setToken(null);
        localStorage.removeItem("smartdocs_token");
        localStorage.removeItem("smartdocs_user");
        window.location.href = "/login";
    }, []);

    // Hydrate auth state on mount
    useEffect(() => {
        const checkAuth = async () => {
            const savedToken = localStorage.getItem("smartdocs_token");
            if (savedToken) {
                try {
                    const res = await api.get<User>("/auth/me", {
                        headers: { Authorization: `Bearer ${savedToken}` },
                    });
                    setToken(savedToken);
                    setUser(res.data);
                } catch (error) {
                    localStorage.removeItem("smartdocs_token");
                    localStorage.removeItem("smartdocs_user");
                } finally {
                    setLoading(false);
                }
            } else {
                setLoading(false);
            }
        };

        checkAuth();
    }, []);

    const login = async (credentials: LoginRequest) => {
        const res = await api.post<LoginResponse>("/auth/login", credentials);
        const { access_token, user: userData } = res.data;
        setToken(access_token);
        setUser(userData);
        localStorage.setItem("smartdocs_token", access_token);
        localStorage.setItem("smartdocs_user", JSON.stringify(userData));
    };

    return (
        <AuthContext.Provider value={{ user, token, loading, isAdmin, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
