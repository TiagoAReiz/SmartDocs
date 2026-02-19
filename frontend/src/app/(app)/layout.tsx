"use client";

import { AuthGuard } from "@/components/auth-guard";
import { Sidebar } from "@/components/sidebar";
import { MobileNav } from "@/components/mobile-nav";

export default function AppLayout({ children }: { children: React.ReactNode }) {
    return (
        <AuthGuard>
            <div className="flex h-screen overflow-hidden bg-background">
                {/* Sidebar hidden on mobile */}
                <div className="hidden md:block">
                    <Sidebar />
                </div>

                <main className="flex-1 overflow-y-auto pb-20 md:pb-0 scroll-smooth">
                    <div className="mx-auto max-w-7xl p-4 lg:p-8 animate-in fade-in duration-500">{children}</div>
                </main>

                <MobileNav />
            </div>
        </AuthGuard>
    );
}
