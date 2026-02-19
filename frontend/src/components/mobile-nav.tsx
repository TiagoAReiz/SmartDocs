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

    const allItems = isAdmin ? [...navItems, ...adminItems] : navItems;

    return (
        <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-white/[0.08] bg-background/80 backdrop-blur-lg md:hidden">
            <nav className="flex h-16 w-full items-center justify-around px-2 pb-safe-area">
                {allItems.map((item) => {
                    const isActive =
                        pathname === item.href || pathname.startsWith(item.href + "/");
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "relative flex flex-1 flex-col items-center justify-center gap-1 py-1 text-[10px] font-medium transition-all duration-300",
                                isActive
                                    ? "text-primary scale-105"
                                    : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            {isActive && (
                                <div className="absolute -top-3 h-0.5 w-8 rounded-full bg-primary shadow-sm shadow-primary/50" />
                            )}
                            <item.icon className={cn("h-5 w-5", isActive && "fill-current/20 drop-shadow-sm")} />
                            <span className="tracking-wide">{item.label}</span>
                        </Link>
                    );
                })}
            </nav>
        </div>
    );
}
