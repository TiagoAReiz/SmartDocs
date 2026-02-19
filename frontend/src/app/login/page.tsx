"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Sparkles, Loader2, Mail, Lock } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const { login } = useAuth();
    const router = useRouter();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email || !password) {
            toast.error("Preencha todos os campos");
            return;
        }
        setIsLoading(true);
        try {
            await login({ email, password });
            router.push("/documents");
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } };
            toast.error(error.response?.data?.detail || "Email ou senha inválidos");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="relative flex min-h-screen items-center justify-center bg-background p-4 overflow-hidden">
            {/* Background gradient accents */}
            <div className="pointer-events-none absolute inset-0 overflow-hidden">
                <div className="absolute -left-40 -top-40 h-[500px] w-[500px] rounded-full bg-primary/20 blur-[120px] animate-pulse" />
                <div className="absolute -bottom-40 -right-40 h-[500px] w-[500px] rounded-full bg-purple-500/10 blur-[120px] animate-pulse delay-1000" />
            </div>

            <Card className="glass-card relative w-full max-w-md border-white/[0.08] shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-500">
                <CardHeader className="items-center space-y-6 pb-2 pt-8">
                    <div className="relative">
                        <div className="relative flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-blue-600 shadow-lg shadow-primary/25">
                            <Sparkles className="h-7 w-7 text-white" />
                        </div>
                    </div>
                    <div className="text-center space-y-1">
                        <h1 className="text-2xl font-bold tracking-tight text-foreground">
                            SmartDocs
                        </h1>
                        <p className="text-sm text-muted-foreground">
                            Gestão inteligente de documentos
                        </p>
                    </div>
                </CardHeader>
                <CardContent className="px-8 pb-8 pt-6">
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-2">
                            <Label htmlFor="email" className="text-sm font-medium text-foreground/80">
                                Email
                            </Label>
                            <div className="relative group">
                                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-foreground" />
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="seu@email.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="h-11 border-white/[0.08] bg-white/[0.03] pl-10 text-foreground placeholder:text-muted-foreground/50 focus-visible:ring-primary/30 transition-all hover:bg-white/[0.05]"
                                    autoComplete="email"
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="password" className="text-sm font-medium text-foreground/80">
                                Senha
                            </Label>
                            <div className="relative group">
                                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-foreground" />
                                <Input
                                    id="password"
                                    type="password"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="h-11 border-white/[0.08] bg-white/[0.03] pl-10 text-foreground placeholder:text-muted-foreground/50 focus-visible:ring-primary/30 transition-all hover:bg-white/[0.05]"
                                    autoComplete="current-password"
                                />
                            </div>
                        </div>
                        <Button
                            type="submit"
                            disabled={isLoading}
                            className="h-11 w-full bg-primary font-medium text-primary-foreground shadow-lg shadow-primary/25 transition-all hover:bg-primary/90 hover:shadow-primary/40 hover:scale-[1.02] disabled:opacity-70 active:scale-[0.98]"
                        >
                            {isLoading ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : null}
                            Entrar na Plataforma
                        </Button>
                    </form>
                </CardContent>
            </Card>

            <p className="absolute bottom-6 text-xs text-muted-foreground/40">
                &copy; 2026 SmartDocs Inc.
            </p>
        </div>
    );
}
