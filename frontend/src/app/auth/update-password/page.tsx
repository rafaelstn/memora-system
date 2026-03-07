"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2, KeyRound } from "lucide-react";
import toast from "react-hot-toast";
import { updatePassword } from "@/lib/auth";

export default function UpdatePasswordPage() {
  const router = useRouter();
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
      await updatePassword(password);
      toast.success("Senha redefinida com sucesso!");
      router.push("/auth/signin");
    } catch (e: unknown) {
      setError("Erro ao redefinir senha. Tente novamente.");
      toast.error(e instanceof Error ? e.message : "Erro inesperado");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm rounded-xl border border-border bg-card-bg p-8">
        <div className="flex items-center justify-center gap-2 mb-8">
          <img src="/icon.png" alt="Memora" className="w-10 h-10 rounded-lg" />
          <span className="text-2xl font-bold">Memora</span>
        </div>

        <div className="flex items-center justify-center mb-6">
          <div className="p-3 rounded-full bg-indigo-500/10">
            <KeyRound size={24} className="text-indigo-400" />
          </div>
        </div>

        <h2 className="text-lg font-semibold text-center mb-1">Redefinir senha</h2>
        <p className="text-sm text-muted text-center mb-6">
          Escolha uma nova senha para sua conta.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Nova senha</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                className="w-full px-3 py-2 pr-10 text-sm rounded-lg border border-border bg-card-bg text-foreground"
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
            <label className="block text-sm font-medium mb-1">Confirmar nova senha</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              autoComplete="new-password"
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground"
            />
            {confirmPassword && confirmPassword !== password && (
              <p className="text-xs text-red-400 mt-1">Senhas não coincidem</p>
            )}
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors disabled:opacity-50"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            Redefinir senha
          </button>
        </form>
      </div>
    </div>
  );
}
