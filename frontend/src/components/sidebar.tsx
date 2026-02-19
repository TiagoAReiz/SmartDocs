"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import {
    FileText,
    MessageSquare,
    Upload,
    Users,
    LogOut,
    Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
    { href: "/documents", label: "Documentos", icon: FileText },
    { href: "/chat", label: "Chat", icon: MessageSquare },
    { href: "/upload", label: "Upload", icon: Upload },
];

const adminItems = [
    { href: "/admin/users", label: "Administração", icon: Users },
];

export function Sidebar() {
    const pathname = usePathname();
    const { user, logout, isAdmin } = useAuth(); // Removed unused 'isLoading' if it was there, kept essential

    const allItems = isAdmin ? [...navItems, ...adminItems] : navItems;

    return (
        <aside className="relative flex h-screen w-64 flex-col border-r border-white/[0.04] bg-sidebar text-sidebar-foreground">
            {/* Logo */}
            <div className="flex h-16 items-center gap-3 px-6">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6] to-[#2563EB] shadow-lg shadow-blue-500/20">
                    <Sparkles className="h-4 w-4 text-white" />
                </div>
                <span className="text-lg font-semibold tracking-tight text-white">
                    SmartDocs
                </span>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1 p-4">
                {allItems.map((item) => {
                    const isActive =
                        pathname === item.href || pathname.startsWith(item.href + "/");
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                                isActive
                                    ? "bg-primary/10 text-primary shadow-sm"
                                    : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
                            )}
                        >
                            <item.icon className={cn("h-[18px] w-[18px]", isActive ? "text-primary" : "text-slate-500 group-hover:text-slate-300")} />
                            {item.label}
                            {isActive && (
                                <div className="absolute right-0 top-0 h-full w-1 rounded-l-full bg-primary opacity-0" />
                            )}
                        </Link>
                    );
                })}
            </nav>

            {/* User section */}
            <div className="border-t border-white/[0.04] p-4">
                <div className="mb-3 flex items-center gap-3 rounded-xl bg-white/[0.03] p-3 border border-white/[0.04]">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary ring-2 ring-background">
                        {user?.name?.charAt(0)?.toUpperCase() || "U"}
                    </div>
                    <div className="flex-1 overflow-hidden">
                        <p className="truncate text-sm font-medium text-slate-200">
                            {user?.name}
                        </p>
                        <p className="truncate text-xs text-slate-500">{user?.email}</p>
                    </div>
                </div>
                <button
                    onClick={logout}
                    className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400 transition-colors hover:bg-red-500/10 hover:text-red-400"
                >
                    <LogOut className="h-[18px] w-[18px]" />
                    Sair
                </button>
            </div>
        </aside>
    );
}
