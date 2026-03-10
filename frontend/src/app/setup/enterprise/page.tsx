"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Database,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertTriangle,
  Server,
} from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "@/lib/hooks/useAuth";
import {
  enterpriseTestConnection,
  enterpriseSetupStream,
} from "@/lib/api";
import type { EnterpriseDBConfig } from "@/lib/api";

interface MigrationStep {
  table: string;
  status: "ok" | "error";
  message: string;
}

export default function EnterpriseSetupPage() {
  const router = useRouter();
  const { user, isLoading: authLoading, refreshUser } = useAuth();

  // Form state
  const [host, setHost] = useState("");
  const [port, setPort] = useState("5432");
  const [database, setDatabase] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [sslMode, setSslMode] = useState("require");
  const [confirmed, setConfirmed] = useState(false);

  // UI state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [migrating, setMigrating] = useState(false);
  const [steps, setSteps] = useState<MigrationStep[]>([]);
  const [progress, setProgress] = useState({ step: 0, total: 0 });
  const [done, setDone] = useState(false);

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-page-bg">
        <Loader2 size={32} className="animate-spin text-muted" />
      </div>
    );
  }

  if (!user || user.role !== "admin") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-page-bg">
        <div className="text-center">
          <AlertTriangle size={40} className="mx-auto text-yellow-500" />
          <p className="mt-4 text-lg font-medium">Acesso restrito</p>
          <p className="mt-1 text-sm text-muted">Apenas administradores podem configurar o banco Enterprise.</p>
        </div>
      </div>
    );
  }

  const config: EnterpriseDBConfig = {
    host,
    port: parseInt(port) || 5432,
    database,
    username,
    password,
    ssl_mode: sslMode,
  };

  const canTest = host && database && username && password;
  const canSetup = canTest && confirmed && testResult?.success;

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await enterpriseTestConnection(config);
      setTestResult({ success: result.success, message: result.message });
    } catch (err) {
      setTestResult({ success: false, message: err instanceof Error ? err.message : "Erro ao testar" });
    } finally {
      setTesting(false);
    }
  };

  const handleSetup = async () => {
    setMigrating(true);
    setSteps([]);
    setProgress({ step: 0, total: 0 });
    setDone(false);

    await enterpriseSetupStream(
      config,
      (event) => {
        if (event.type === "progress") {
          const step = event as unknown as { step: number; total: number; table: string; status: "ok" | "error"; message: string };
          setProgress({ step: step.step, total: step.total });
          setSteps((prev) => [...prev, { table: step.table, status: step.status, message: step.message }]);
        }
        if (event.type === "done") {
          if (event.success) {
            setDone(true);
            toast.success("Banco configurado com sucesso!");
            refreshUser();
            setTimeout(() => router.push("/dashboard"), 2000);
          } else {
            toast.error(String(event.message || "Erro durante setup"));
          }
        }
        if (event.type === "error") {
          toast.error(String(event.message || "Erro inesperado"));
        }
      },
      () => {
        setMigrating(false);
      },
      (err) => {
        toast.error(err);
        setMigrating(false);
      },
    );
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-page-bg p-4">
      <div className="w-full max-w-xl space-y-6">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-surface">
            <Server size={32} className="text-accent-text" />
          </div>
          <h1 className="mt-4 text-2xl font-bold">Configure o banco de dados do seu Memora</h1>
          <p className="mt-2 text-sm text-muted">
            Informe as credenciais do banco PostgreSQL onde os dados operacionais serao armazenados.
          </p>
        </div>

        {/* Form */}
        <div className="rounded-2xl border border-border bg-card-bg p-6 space-y-4" style={{ boxShadow: "var(--shadow-md)" }}>
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1.5">Host</label>
              <input
                type="text"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                placeholder="db.minhaempresa.com"
                disabled={migrating}
                className="w-full rounded-lg border border-border bg-input-bg px-3 py-2 text-sm outline-none focus:border-accent transition-colors disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">Porta</label>
              <input
                type="text"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                placeholder="5432"
                disabled={migrating}
                className="w-full rounded-lg border border-border bg-input-bg px-3 py-2 text-sm outline-none focus:border-accent transition-colors disabled:opacity-50"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Nome do banco</label>
            <input
              type="text"
              value={database}
              onChange={(e) => setDatabase(e.target.value)}
              placeholder="memora_prod"
              disabled={migrating}
              className="w-full rounded-lg border border-border bg-input-bg px-3 py-2 text-sm outline-none focus:border-accent transition-colors disabled:opacity-50"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">Usuario</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="memora_user"
                disabled={migrating}
                className="w-full rounded-lg border border-border bg-input-bg px-3 py-2 text-sm outline-none focus:border-accent transition-colors disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">Senha</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                disabled={migrating}
                className="w-full rounded-lg border border-border bg-input-bg px-3 py-2 text-sm outline-none focus:border-accent transition-colors disabled:opacity-50"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">SSL Mode</label>
            <select
              value={sslMode}
              onChange={(e) => setSslMode(e.target.value)}
              disabled={migrating}
              className="w-full rounded-lg border border-border bg-input-bg px-3 py-2 text-sm outline-none focus:border-accent transition-colors disabled:opacity-50"
            >
              <option value="require">require</option>
              <option value="prefer">prefer</option>
              <option value="disable">disable</option>
            </select>
          </div>

          {/* Test connection */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleTest}
              disabled={!canTest || testing || migrating}
              className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-hover transition-colors disabled:opacity-50"
            >
              {testing ? <Loader2 size={14} className="animate-spin" /> : <Database size={14} />}
              Testar conexao
            </button>

            {testResult && (
              <div className={`flex items-center gap-1.5 text-sm ${testResult.success ? "text-green-600" : "text-red-500"}`}>
                {testResult.success ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                <span className="truncate max-w-xs">{testResult.message}</span>
              </div>
            )}
          </div>
        </div>

        {/* Warning box */}
        <div className="rounded-xl border border-yellow-500/30 bg-yellow-500/5 p-4 space-y-3">
          <div className="flex items-start gap-2">
            <AlertTriangle size={18} className="mt-0.5 shrink-0 text-yellow-600" />
            <p className="text-sm text-yellow-700 dark:text-yellow-400">
              <strong>Atencao:</strong> O banco de dados informado deve estar limpo e vazio.
              O Memora ira criar automaticamente todas as tabelas necessarias para o funcionamento do sistema.
              Dados existentes podem ser afetados caso o banco nao esteja limpo.
              Ao continuar, voce confirma que esta ciente disso e que as credenciais informadas
              tem permissao para criar tabelas e indices.
            </p>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
              disabled={migrating}
              className="h-4 w-4 rounded border-border accent-accent"
            />
            <span className="text-sm font-medium">Estou ciente e confirmo</span>
          </label>
        </div>

        {/* Setup button */}
        <button
          onClick={handleSetup}
          disabled={!canSetup || migrating}
          className="w-full flex items-center justify-center gap-2 rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-white hover:bg-accent/90 transition-colors disabled:opacity-50"
        >
          {migrating ? <Loader2 size={16} className="animate-spin" /> : <Server size={16} />}
          {migrating ? "Configurando..." : "Configurar e criar tabelas"}
        </button>

        {/* Migration progress */}
        {steps.length > 0 && (
          <div className="rounded-2xl border border-border bg-card-bg p-5 space-y-3" style={{ boxShadow: "var(--shadow-md)" }}>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Progresso das migrations</h3>
              <span className="text-xs text-muted">
                {progress.step}/{progress.total}
              </span>
            </div>

            {/* Progress bar */}
            <div className="h-2 w-full rounded-full bg-hover overflow-hidden">
              <div
                className="h-full rounded-full bg-accent transition-all duration-300"
                style={{ width: progress.total ? `${(progress.step / progress.total) * 100}%` : "0%" }}
              />
            </div>

            {/* Steps list */}
            <div className="max-h-48 overflow-y-auto space-y-1">
              {steps.map((s, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  {s.status === "ok" ? (
                    <CheckCircle2 size={12} className="shrink-0 text-green-500" />
                  ) : (
                    <XCircle size={12} className="shrink-0 text-red-500" />
                  )}
                  <span className="truncate text-muted">{s.table}</span>
                </div>
              ))}
            </div>

            {done && (
              <div className="flex items-center gap-2 pt-2 text-sm font-medium text-green-600">
                <CheckCircle2 size={16} />
                Setup concluido! Redirecionando...
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
