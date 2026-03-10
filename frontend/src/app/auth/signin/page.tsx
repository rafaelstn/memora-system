"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2, Mail, ArrowLeft, UserPlus } from "lucide-react";
import toast from "react-hot-toast";
import { signIn, signUp, resetPassword } from "@/lib/auth";

type AuthState = "login" | "register" | "reset";

function getPasswordStrength(pw: string): { label: string; color: string; width: string } {
  if (pw.length < 8) return { label: "Fraca", color: "bg-red-500", width: "w-1/4" };
  const hasUpper = /[A-Z]/.test(pw);
  const hasNumber = /\d/.test(pw);
  const hasSpecial = /[^A-Za-z0-9]/.test(pw);
  const score = [hasUpper, hasNumber, hasSpecial, pw.length >= 12].filter(Boolean).length;
  if (score >= 3) return { label: "Forte", color: "bg-green-500", width: "w-full" };
  if (score >= 2) return { label: "Média", color: "bg-yellow-500", width: "w-2/3" };
  return { label: "Fraca", color: "bg-red-500", width: "w-1/3" };
}

export default function SignInPage() {
  const router = useRouter();
  const [state, setState] = useState<AuthState>("login");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState("");
  const [resetSent, setResetSent] = useState(false);
  const [hasInvite, setHasInvite] = useState(false);

  // Form fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [inviteToken, setInviteToken] = useState("");
  const [orgName, setOrgName] = useState("");

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  function clearForm() {
    setEmail("");
    setPassword("");
    setName("");
    setConfirmPassword("");
    setInviteToken("");
    setOrgName("");
    setError("");
    setResetSent(false);
    setShowPassword(false);
    setShowConfirmPassword(false);
    setHasInvite(false);
  }

  function switchState(newState: AuthState) {
    clearForm();
    setState(newState);
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await signIn(email, password);
      router.push("/dashboard");
    } catch (e: unknown) {
      setError("Email ou senha incorretos");
      toast.error(e instanceof Error ? e.message : "Erro inesperado");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(e: React.FormEvent) {
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
      const user = await signUp(name, email, password, inviteToken || undefined, orgName || undefined);
      if (user.role === "admin") {
        toast.success("Conta criada! Você é administrador do sistema.");
      } else {
        toast.success("Bem-vindo ao Memora!");
      }
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erro ao criar conta");
    } finally {
      setLoading(false);
    }
  }

  async function handleReset(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await resetPassword(email);
      setResetSent(true);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Erro inesperado");
      setResetSent(true); // Mensagem genérica por segurança
    } finally {
      setLoading(false);
    }
  }

  const strength = getPasswordStrength(password);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card-bg p-8" style={{ boxShadow: "var(--shadow-lg)" }}>
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <img src="/logo-icon.png" alt="Memora" className="w-10 h-10 rounded-lg dark:hidden" />
          <img src="/logo-white.png" alt="Memora" className="w-10 h-10 rounded-lg hidden dark:block" />
          <span className="text-2xl font-bold">Memora</span>
        </div>


        {/* === LOGIN STATE === */}
        {state === "login" && (
          <form onSubmit={handleLogin} className="space-y-4">
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
                  autoComplete="current-password"
                  className="w-full px-3 py-2.5 pr-10 text-sm rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-colors"
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

            {error && <p className="text-sm text-red-400">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium rounded-xl bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
            >
              {loading && <Loader2 size={16} className="animate-spin" />}
              Entrar
            </button>

            <div className="flex items-center justify-between text-xs">
              <button
                type="button"
                onClick={() => switchState("reset")}
                className="text-muted hover:text-foreground transition-colors"
              >
                Esqueci minha senha
              </button>
              <button
                type="button"
                onClick={() => switchState("register")}
                className="text-accent hover:text-accent-light font-medium transition-colors flex items-center gap-1"
              >
                <UserPlus size={12} />
                Criar conta
              </button>
            </div>
          </form>
        )}

        {/* === REGISTER STATE === */}
        {state === "register" && (
          <form onSubmit={handleRegister} className="space-y-4">
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
              {password.length > 0 && (
                <div className="mt-1.5 flex items-center gap-2">
                  <div className="flex-1 h-1 rounded-full bg-border overflow-hidden">
                    <div className={`h-full ${strength.color} ${strength.width} transition-all`} />
                  </div>
                  <span className="text-xs text-muted">{strength.label}</span>
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Confirmar senha</label>
              <div className="relative">
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  className="w-full px-3 py-2.5 pr-10 text-sm rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-foreground"
                >
                  {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {confirmPassword && confirmPassword !== password && (
                <p className="text-xs text-red-400 mt-1">Senhas não coincidem</p>
              )}
            </div>

            {!hasInvite ? (
              <div>
                <label className="block text-sm font-medium mb-1">Nome da empresa</label>
                <input
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  required
                  className="w-full px-3 py-2.5 text-sm rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-colors"
                  placeholder="Sua empresa"
                />
                <button
                  type="button"
                  onClick={() => setHasInvite(true)}
                  className="text-xs text-muted hover:text-foreground mt-1 transition-colors"
                >
                  Tenho um código de convite
                </button>
              </div>
            ) : (
              <div>
                <label className="block text-sm font-medium mb-1">Código de convite</label>
                <input
                  type="text"
                  value={inviteToken}
                  onChange={(e) => setInviteToken(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground font-mono"
                  placeholder="abc12345-xxxx-yyyy"
                />
                <button
                  type="button"
                  onClick={() => setHasInvite(false)}
                  className="text-xs text-muted hover:text-foreground mt-1 transition-colors"
                >
                  Criar nova empresa
                </button>
              </div>
            )}

            {error && <p className="text-sm text-red-400">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium rounded-xl bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
            >
              {loading && <Loader2 size={16} className="animate-spin" />}
              Criar conta
            </button>

            <button
              type="button"
              onClick={() => switchState("login")}
              className="w-full text-center text-xs text-muted hover:text-foreground transition-colors flex items-center justify-center gap-1"
            >
              <ArrowLeft size={12} />
              Já tenho conta
            </button>
          </form>
        )}

        {/* === RESET PASSWORD STATE === */}
        {state === "reset" && (
          <div className="space-y-4">
            {!resetSent ? (
              <form onSubmit={handleReset} className="space-y-4">
                <p className="text-sm text-muted text-center">
                  Digite seu email para receber o link de redefinição.
                </p>
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

                {error && <p className="text-sm text-red-400">{error}</p>}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium rounded-xl bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
                >
                  {loading && <Loader2 size={16} className="animate-spin" />}
                  <Mail size={16} />
                  Enviar link de redefinição
                </button>

                <button
                  type="button"
                  onClick={() => switchState("login")}
                  className="w-full text-center text-xs text-muted hover:text-foreground transition-colors flex items-center justify-center gap-1"
                >
                  <ArrowLeft size={12} />
                  Voltar para login
                </button>
              </form>
            ) : (
              <div className="text-center space-y-4">
                <div className="p-3 rounded-full bg-success-surface w-fit mx-auto">
                  <Mail size={24} className="text-success" />
                </div>
                <p className="text-sm text-muted">
                  Se este email estiver cadastrado, você receberá um link em instantes.
                </p>
                <button
                  type="button"
                  onClick={() => switchState("login")}
                  className="text-xs text-accent hover:text-accent-light transition-colors flex items-center justify-center gap-1 mx-auto"
                >
                  <ArrowLeft size={12} />
                  Voltar para login
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
