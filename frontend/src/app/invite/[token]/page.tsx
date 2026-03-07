"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2, AlertCircle } from "lucide-react";
import toast from "react-hot-toast";
import { signUp } from "@/lib/auth";

export default function InvitePage() {
  const params = useParams();
  const router = useRouter();
  const inviteToken = params.token as string;

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Senha deve ter no mínimo 8 caracteres");
      return;
    }
    if (password !== confirmPassword) {
      setError("Senhas não coincidem");
      return;
    }

    setLoading(true);
    try {
      await signUp(name, email, password, inviteToken);
      toast.success("Bem-vindo ao Memora!");
      router.push("/dashboard");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Erro ao criar conta";
      if (message.includes("inválido") || message.includes("expirado")) {
        setError("Convite inválido ou expirado. Solicite um novo ao administrador.");
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card-bg p-8" style={{ boxShadow: "var(--shadow-lg)" }}>
        <div className="flex items-center justify-center gap-2 mb-6">
          <img src="/icon.png" alt="Memora" className="w-10 h-10 rounded-lg" />
          <span className="text-2xl font-bold">Memora</span>
        </div>

        <h2 className="text-lg font-semibold text-center mb-1">Criar sua conta</h2>
        <p className="text-sm text-muted text-center mb-6">
          Você foi convidado para participar do Memora.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Nome completo</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2.5 text-sm rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-colors"
              placeholder="Seu nome"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="w-full px-3 py-2.5 text-sm rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-colors"
              placeholder="seu@email.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Senha</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                className="w-full px-3 py-2.5 pr-10 text-sm rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-colors"
                placeholder="Mínimo 8 caracteres"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-foreground"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Confirmar senha</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              autoComplete="new-password"
              className="w-full px-3 py-2.5 text-sm rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-colors"
            />
            {confirmPassword && confirmPassword !== password && (
              <p className="text-xs text-red-400 mt-1">Senhas não coincidem</p>
            )}
          </div>

          {error && (
            <div className="flex items-start gap-2 p-3 rounded-xl bg-danger-surface border border-danger/20">
              <AlertCircle size={16} className="text-danger mt-0.5 shrink-0" />
              <p className="text-sm text-danger">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            Criar conta
          </button>
        </form>
      </div>
    </div>
  );
}
