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
        <div className="relative flex min-h-screen items-center justify-center bg-[#0F172A] p-4">
            {/* Background gradient accents */}
            <div className="pointer-events-none absolute inset-0 overflow-hidden">
                <div className="absolute -left-40 -top-40 h-80 w-80 rounded-full bg-[#136dec]/10 blur-[100px]" />
                <div className="absolute -bottom-40 -right-40 h-80 w-80 rounded-full bg-[#136dec]/5 blur-[100px]" />
            </div>

            <Card className="glass relative w-full max-w-md border-white/[0.08] bg-[#1E293B]/70 shadow-2xl shadow-black/20">
                <CardHeader className="items-center space-y-4 pb-2">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#136dec] shadow-lg shadow-[#136dec]/25">
                        <Sparkles className="h-6 w-6 text-white" />
                    </div>
                    <div className="text-center">
                        <h1 className="text-2xl font-semibold tracking-tight text-white">
                            SmartDocs
                        </h1>
                        <p className="mt-1 text-sm text-slate-400">
                            Gestão inteligente de documentos
                        </p>
                    </div>
                </CardHeader>
                <CardContent className="pt-4">
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-2">
                            <Label htmlFor="email" className="text-sm text-slate-300">
                                Email
                            </Label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="seu@email.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="h-11 border-white/[0.08] bg-white/[0.04] pl-10 text-slate-200 placeholder:text-slate-600 focus:border-[#136dec]/50 focus:ring-[#136dec]/20"
                                    autoComplete="email"
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="password" className="text-sm text-slate-300">
                                Senha
                            </Label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                                <Input
                                    id="password"
                                    type="password"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="h-11 border-white/[0.08] bg-white/[0.04] pl-10 text-slate-200 placeholder:text-slate-600 focus:border-[#136dec]/50 focus:ring-[#136dec]/20"
                                    autoComplete="current-password"
                                />
                            </div>
                        </div>
                        <Button
                            type="submit"
                            disabled={isLoading}
                            className="h-11 w-full bg-[#136dec] font-medium text-white shadow-lg shadow-[#136dec]/25 transition-all hover:bg-[#1178ff] hover:shadow-[#136dec]/30 disabled:opacity-60"
                        >
                            {isLoading ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : null}
                            Entrar
                        </Button>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
}
