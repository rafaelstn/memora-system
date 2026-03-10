import Image from "next/image";
import Link from "next/link";
import {
  MessageSquare,
  Shield,
  Brain,
  ArrowRight,
  Eye,
  Zap,
  Clock,
  ShieldCheck,
  Database,
  GitBranch,
  Settings,
  BarChart3,
  Check,
  Crown,
  Building2,
  Sparkles,
  Star,
} from "lucide-react";
import { cn } from "@/lib/utils";

function ModuleCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="group relative rounded-2xl border border-white/[0.08] bg-white/[0.03] p-6 backdrop-blur-sm transition-all duration-300 hover:border-white/[0.15] hover:bg-white/[0.06]">
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-indigo-500/[0.05] to-purple-500/[0.05] opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      <div className="relative flex flex-col gap-4">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 ring-1 ring-white/[0.08]">
          <Icon className="h-5 w-5 text-indigo-300" />
        </div>
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        <p className="text-sm leading-relaxed text-slate-400">{description}</p>
      </div>
    </div>
  );
}

function StepCard({
  number,
  icon: Icon,
  title,
  description,
}: {
  number: number;
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center gap-5 text-center">
      <div className="relative">
        <div className="absolute -inset-3 rounded-full bg-gradient-to-br from-indigo-500/20 to-purple-500/20 blur-lg" />
        <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/25">
          <Icon className="h-7 w-7" />
        </div>
        <span className="absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-full bg-white text-xs font-bold text-slate-900">
          {number}
        </span>
      </div>
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="max-w-xs text-sm leading-relaxed text-slate-400">
        {description}
      </p>
    </div>
  );
}

function BenefitCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center gap-4 rounded-2xl border border-white/[0.08] bg-white/[0.03] p-8 text-center backdrop-blur-sm">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 ring-1 ring-white/[0.08]">
        <Icon className="h-6 w-6 text-indigo-300" />
      </div>
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="text-sm leading-relaxed text-slate-400">{description}</p>
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0b0f1a] text-slate-200 overflow-hidden">
      {/* Navbar */}
      <nav className="relative z-10 border-b border-white/[0.06]">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Image
              src="/logo.png"
              alt="Memora"
              width={32}
              height={32}
              className="h-8 w-8 rounded-lg"
            />
            <span className="text-lg font-bold tracking-tight text-white">
              Memora
            </span>
          </div>
          <div className="flex items-center gap-6">
            <Link
              href="#precos"
              className="text-sm text-slate-400 transition-colors hover:text-white"
            >
              Precos
            </Link>
            <Link
              href="/auth/signin"
              className="rounded-lg bg-white/[0.08] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-white/[0.15]"
            >
              Entrar
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative">
        {/* Gradient orbs */}
        <div className="pointer-events-none absolute -top-40 left-1/2 h-[600px] w-[800px] -translate-x-1/2 rounded-full bg-gradient-to-br from-indigo-600/20 via-purple-600/10 to-transparent blur-3xl" />
        <div className="pointer-events-none absolute right-0 top-20 h-[400px] w-[400px] rounded-full bg-purple-600/10 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-6 pb-20 pt-24 md:pb-28 md:pt-32">
          <div className="flex flex-col items-center text-center">
            <span className="mb-6 inline-flex items-center rounded-full border border-indigo-400/20 bg-indigo-500/10 px-4 py-1.5 text-xs font-medium text-indigo-300">
              Inteligencia Tecnica Operacional para PMEs
            </span>

            <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-6xl">
              <span className="bg-gradient-to-r from-white via-white to-slate-400 bg-clip-text text-transparent">
                Inteligencia Tecnica
              </span>
              <br />
              <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                para PMEs
              </span>
            </h1>

            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-400">
              Memora indexa seu codigo, monitora erros, preserva conhecimento e
              revisa PRs automaticamente. Tudo em uma plataforma com IA — feita
              para times brasileiros que precisam escalar sem perder controle.
            </p>

            <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
              <Link
                href="/auth/signin"
                className={cn(
                  "inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-7 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25",
                  "transition-all duration-200 hover:shadow-indigo-500/40 hover:scale-[1.03]"
                )}
              >
                Comecar Agora
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="#modulos"
                className="inline-flex items-center gap-2 rounded-xl border border-white/[0.1] px-7 py-3.5 text-sm font-medium text-slate-300 transition-colors hover:bg-white/[0.06] hover:text-white"
              >
                Conhecer os modulos
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Modules */}
      <section id="modulos" className="relative border-t border-white/[0.06]">
        <div className="pointer-events-none absolute left-0 top-0 h-[300px] w-[300px] rounded-full bg-indigo-600/10 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-28">
          <h2 className="mb-4 text-center text-3xl font-bold tracking-tight text-white">
            Quatro modulos. Uma plataforma.
          </h2>
          <p className="mx-auto mb-14 max-w-2xl text-center text-slate-400">
            Cada modulo resolve um problema real do seu time — e todos trabalham
            juntos para dar contexto completo sobre o seu sistema.
          </p>

          <div className="grid gap-6 sm:grid-cols-2">
            <ModuleCard
              icon={MessageSquare}
              title="Code Intelligence"
              description="Indexa seu codigo via AST, gera embeddings e responde perguntas em portugues com busca hibrida (semantica + full-text). O suporte resolve sem acionar o dev."
            />
            <ModuleCard
              icon={Shield}
              title="Error Monitor"
              description="Recebe logs do seu sistema, analisa com IA, gera alertas com explicacoes em portugues e notifica via email e webhooks. Detecta erros antes do cliente perceber."
            />
            <ModuleCard
              icon={Brain}
              title="Technical Memory"
              description="Captura conhecimento de PRs, commits, issues e documentos. Gera wikis automaticas por componente. O conhecimento nunca mais vai embora com um dev."
            />
            <ModuleCard
              icon={Eye}
              title="Code Review"
              description="Revisa PRs automaticamente em 5 categorias paralelas: bugs, seguranca, performance, consistencia e padroes. Posta comentarios formatados direto no GitHub."
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="relative border-t border-white/[0.06] bg-white/[0.02]">
        <div className="pointer-events-none absolute right-0 bottom-0 h-[400px] w-[400px] rounded-full bg-purple-600/10 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-28">
          <h2 className="mb-4 text-center text-3xl font-bold tracking-tight text-white">
            Como funciona
          </h2>
          <p className="mx-auto mb-14 max-w-2xl text-center text-slate-400">
            Em tres passos seu time ja esta operando com inteligencia tecnica.
          </p>

          <div className="grid gap-12 sm:grid-cols-3 sm:gap-8">
            <StepCard
              number={1}
              icon={GitBranch}
              title="Conecte seu repositorio"
              description="Integre com GitHub em um clique. O Memora indexa todo o codigo, gera embeddings e monta a base de conhecimento automaticamente."
            />
            <StepCard
              number={2}
              icon={Settings}
              title="Configure o monitor"
              description="Instale o agente de logs ou envie via API. O Memora analisa erros em tempo real e notifica seu time com explicacoes claras."
            />
            <StepCard
              number={3}
              icon={BarChart3}
              title="Receba insights"
              description="Painel executivo com metricas semanais, historico de saude, exportacao de dados e alertas proativos. Controle total."
            />
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="relative border-t border-white/[0.06]">
        <div className="pointer-events-none absolute left-1/2 top-0 h-[300px] w-[600px] -translate-x-1/2 rounded-full bg-gradient-to-br from-indigo-600/10 to-purple-600/10 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-28">
          <h2 className="mb-4 text-center text-3xl font-bold tracking-tight text-white">
            Por que times escolhem o Memora
          </h2>
          <p className="mx-auto mb-14 max-w-2xl text-center text-slate-400">
            Resultado real, mensuravel desde a primeira semana.
          </p>

          <div className="grid gap-6 sm:grid-cols-3">
            <BenefitCard
              icon={Clock}
              title="Economia de tempo"
              description="Suporte responde sem dev. Erros sao explicados automaticamente. PRs revisados em segundos. Seu time foca no que importa."
            />
            <BenefitCard
              icon={ShieldCheck}
              title="Seguranca proativa"
              description="Erros detectados antes do cliente. Vulnerabilidades encontradas no PR. Incidentes com historico e postmortem automatico."
            />
            <BenefitCard
              icon={Database}
              title="Conhecimento centralizado"
              description="Decisoes, mudancas e motivos registrados para sempre. Documentacao automatica. Zero perda em turnover de devs."
            />
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="precos" className="relative border-t border-white/[0.06] bg-white/[0.02]">
        <div className="pointer-events-none absolute right-0 top-0 h-[400px] w-[400px] rounded-full bg-indigo-600/10 blur-3xl" />
        <div className="pointer-events-none absolute left-0 bottom-0 h-[300px] w-[300px] rounded-full bg-purple-600/10 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-28">
          <h2 className="mb-4 text-center text-3xl font-bold tracking-tight text-white">
            Planos
          </h2>
          <p className="mx-auto mb-14 max-w-2xl text-center text-slate-400">
            Escolha o plano ideal para o seu time. Todos incluem os 11 modulos do Memora.
          </p>

          <div className="grid gap-6 lg:grid-cols-3">
            {/* PRO */}
            <div className="relative rounded-2xl border-2 border-indigo-500/40 bg-white/[0.04] p-8 backdrop-blur-sm">
              <div className="absolute -top-3 left-6">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 px-3 py-1 text-xs font-semibold text-white shadow-lg shadow-indigo-500/25">
                  <Crown className="h-3 w-3" />
                  Mais popular
                </span>
              </div>

              <div className="mt-4 flex flex-col gap-6">
                <div>
                  <h3 className="text-xl font-bold text-white">PRO</h3>
                  <p className="mt-1 text-sm text-slate-400">Por time (ate 10 devs)</p>
                </div>

                <div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold text-white">R$497</span>
                    <span className="text-sm text-slate-400">/mes</span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">
                    Um dev interrompido 2x a menos por dia ja paga o plano.
                  </p>
                </div>

                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-2.5">
                  <p className="text-sm font-medium text-emerald-300">
                    Trial de 7 dias gratis — sem cartao de credito
                  </p>
                </div>

                <ul className="flex flex-col gap-3">
                  {[
                    "Todos os 11 modulos",
                    "Multi-repositorio",
                    "Multi-usuario (ate 10)",
                    "Infraestrutura Memora (Supabase)",
                    "Suporte por email",
                    "Atualizacoes automaticas",
                  ].map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-slate-300">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
                      {f}
                    </li>
                  ))}
                </ul>

                <Link
                  href="https://memora-system.vercel.app/auth/signin"
                  className={cn(
                    "mt-auto inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25",
                    "transition-all duration-200 hover:shadow-indigo-500/40 hover:scale-[1.03]"
                  )}
                >
                  Comecar trial de 7 dias
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </div>

            {/* Enterprise */}
            <div className="relative rounded-2xl border border-white/[0.08] bg-white/[0.03] p-8 backdrop-blur-sm">
              <div className="absolute -top-3 left-6">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.15] bg-white/[0.08] px-3 py-1 text-xs font-semibold text-slate-200">
                  <ShieldCheck className="h-3 w-3" />
                  Seguranca maxima
                </span>
              </div>

              <div className="mt-4 flex flex-col gap-6">
                <div>
                  <h3 className="text-xl font-bold text-white">Enterprise</h3>
                  <p className="mt-1 text-sm text-slate-400">Para times que precisam de controle total</p>
                </div>

                <div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold text-white">R$1.497</span>
                    <span className="text-sm text-slate-400">/mes</span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">
                    Ativacao sob consulta
                  </p>
                </div>

                <ul className="flex flex-col gap-3">
                  {[
                    "Tudo do PRO",
                    "Banco de dados na sua infra",
                    "Compliance total (LGPD)",
                    "Dados nunca saem do seu ambiente",
                    "SSO e controle de acesso avancado",
                    "SLA dedicado",
                    "Suporte prioritario",
                  ].map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-slate-300">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
                      {f}
                    </li>
                  ))}
                </ul>

                <Link
                  href="mailto:rafael@orbitalis.com.br?subject=Memora Enterprise"
                  className="mt-auto inline-flex items-center justify-center gap-2 rounded-xl border border-white/[0.1] px-6 py-3.5 text-sm font-semibold text-white transition-colors hover:bg-white/[0.06]"
                >
                  Falar com a equipe
                  <Building2 className="h-4 w-4" />
                </Link>
              </div>
            </div>

            {/* Customer */}
            <div className="relative rounded-2xl border border-white/[0.08] bg-white/[0.03] p-8 backdrop-blur-sm">
              <div className="absolute -top-3 left-6">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/20 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-300">
                  <Sparkles className="h-3 w-3" />
                  Sob medida
                </span>
              </div>

              <div className="mt-4 flex flex-col gap-6">
                <div>
                  <h3 className="text-xl font-bold text-white">Customer</h3>
                  <p className="mt-1 text-sm text-slate-400">Implementacao personalizada na sua operacao</p>
                </div>

                <div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold text-white">Entre em contato</span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">
                    Preco sob medida para sua operacao
                  </p>
                </div>

                <ul className="flex flex-col gap-3">
                  {[
                    "Tudo do Enterprise",
                    "Modulos personalizados sob demanda",
                    "Integracao com sistemas existentes",
                    "Consultoria de implementacao",
                    "Treinamento do time",
                    "Suporte dedicado",
                  ].map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-slate-300">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
                      {f}
                    </li>
                  ))}
                </ul>

                <Link
                  href="mailto:rafael@orbitalis.com.br?subject=Memora Customer"
                  className="mt-auto inline-flex items-center justify-center gap-2 rounded-xl border border-white/[0.1] px-6 py-3.5 text-sm font-semibold text-white transition-colors hover:bg-white/[0.06]"
                >
                  Falar com a equipe
                  <Sparkles className="h-4 w-4" />
                </Link>
              </div>
            </div>
          </div>

          {/* Early adopter note */}
          <div className="mt-8 flex items-center justify-center gap-2 text-center">
            <Star className="h-4 w-4 text-amber-400/70" />
            <p className="text-sm text-slate-500">
              Primeiros 3 clientes: <span className="text-amber-400/80 font-medium">R$397/mes</span> — preco travado para sempre.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative border-t border-white/[0.06]">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-indigo-600/5 to-transparent" />

        <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-28 text-center">
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Pronto para ter controle total do seu sistema?
          </h2>
          <p className="mx-auto mb-10 max-w-xl text-lg text-slate-400">
            Comece com 7 dias gratis. Sem cartao de credito. Configuracao em 15 minutos.
          </p>

          <Link
            href="https://memora-system.vercel.app/auth/signin"
            className={cn(
              "inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-8 py-4 text-base font-semibold text-white shadow-lg shadow-indigo-500/25",
              "transition-all duration-200 hover:shadow-indigo-500/40 hover:scale-[1.03]"
            )}
          >
            Comecar trial de 7 dias
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/[0.06]">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <div className="flex items-center gap-2">
              <Image
                src="/logo.png"
                alt="Memora"
                width={24}
                height={24}
                className="h-6 w-6 rounded-md"
              />
              <span className="text-sm text-slate-500">
                &copy; 2026 Memora &mdash; Orbitalis
              </span>
            </div>
            <div className="flex items-center gap-6 text-sm text-slate-500">
              <Link
                href="/auth/signin"
                className="transition-colors hover:text-slate-300"
              >
                Entrar
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
