"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import {
    FileText,
    MessageSquare,
    Upload,
    Users,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
    { href: "/documents", label: "Docs", icon: FileText },
    { href: "/chat", label: "Chat", icon: MessageSquare },
    { href: "/upload", label: "Upload", icon: Upload },
];

const adminItems = [
    { href: "/admin/users", label: "Admin", icon: Users },
];

export function MobileNav() {
    const pathname = usePathname();
    const { isAdmin } = useAuth();

    // Combine items if admin, otherwise just navItems
    // Ideally we want to keep it to 4-5 items max for mobile bottom bar
    const allItems = isAdmin ? [...navItems, ...adminItems] : navItems;

    return (
        <div className="fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center border-t border-white/[0.06] bg-[#0B1120] md:hidden">
            <nav className="flex w-full justify-around px-2">
                {allItems.map((item) => {
                    const isActive =
                        pathname === item.href || pathname.startsWith(item.href + "/");
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex flex-1 flex-col items-center justify-center gap-1 rounded-lg py-2 text-[10px] font-medium transition-colors",
                                isActive
                                    ? "text-[#136dec]"
                                    : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
                            )}
                        >
                            <item.icon className={cn("h-5 w-5", isActive && "fill-current/20")} />
                            <span>{item.label}</span>
                        </Link>
                    );
                })}
            </nav>
        </div>
    );
}
