"use client";

import { AuthGuard } from "@/components/auth-guard";
import { Sidebar } from "@/components/sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
    return (
        <AuthGuard>
            <div className="flex h-screen overflow-hidden bg-[#0F172A]">
                <Sidebar />
                <main className="flex-1 overflow-y-auto">
                    <div className="mx-auto max-w-7xl p-6 lg:p-8">{children}</div>
                </main>
            </div>
        </AuthGuard>
    );
}
