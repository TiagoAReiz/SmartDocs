"use client";

import { useAuth } from "@/contexts/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Loader2 } from "lucide-react";

interface AuthGuardProps {
    children: React.ReactNode;
    adminOnly?: boolean;
}

export function AuthGuard({ children, adminOnly = false }: AuthGuardProps) {
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!loading && !user) {
            router.replace("/login");
        }
        if (!loading && user && adminOnly && user.role !== "admin") {
            router.replace("/documents");
        }
    }, [user, loading, adminOnly, router]);

    if (loading) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-[#0F172A]">
                <Loader2 className="h-8 w-8 animate-spin text-[#136dec]" />
            </div>
        );
    }

    if (!user) return null;
    if (adminOnly && user.role !== "admin") return null;

    return <>{children}</>;
}
