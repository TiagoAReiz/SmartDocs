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
    const { user, logout, isAdmin } = useAuth();

    const allItems = isAdmin ? [...navItems, ...adminItems] : navItems;

    return (
        <aside className="flex h-screen w-64 flex-col border-r border-white/[0.06] bg-[#0B1120]">
            {/* Logo */}
            <div className="flex h-16 items-center gap-2.5 border-b border-white/[0.06] px-6">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#136dec]">
                    <Sparkles className="h-4 w-4 text-white" />
                </div>
                <span className="text-lg font-semibold text-white tracking-tight">
                    SmartDocs
                </span>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1 p-3">
                {allItems.map((item) => {
                    const isActive =
                        pathname === item.href || pathname.startsWith(item.href + "/");
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                                isActive
                                    ? "bg-[#136dec]/15 text-[#136dec]"
                                    : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
                            )}
                        >
                            <item.icon className="h-[18px] w-[18px]" />
                            {item.label}
                        </Link>
                    );
                })}
            </nav>

            {/* User section */}
            <div className="border-t border-white/[0.06] p-3">
                <div className="mb-2 flex items-center gap-3 rounded-lg px-3 py-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#136dec]/20 text-xs font-semibold text-[#136dec]">
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
                    className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-500 transition-colors hover:bg-white/[0.04] hover:text-red-400"
                >
                    <LogOut className="h-[18px] w-[18px]" />
                    Sair
                </button>
            </div>
        </aside>
    );
}
