"use client";

import Link from "next/link";
import Image from "next/image";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRight,
  Check,
  Crown,
  Building2,
  Sparkles,
  Star,
  ShieldCheck,
  ChevronDown,
  MessageSquare,
  AlertTriangle,
  BookOpen,
  FileSearch,
  FileText,
  Scale,
  Code2,
  GitCompare,
  Siren,
  LineChart,
  Shield,
  Brain,
  Zap,
  Clock,
  Users,
  Globe,
} from "lucide-react";
import { I18nProvider, useI18n } from "@/lib/i18n";

// ── Animation helpers ──────────────────────────────────

function FadeIn({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ── Typewriter effect ──────────────────────────────────

function Typewriter({ text, speed = 30 }: { text: string; speed?: number }) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    setDisplayed("");
    setDone(false);
    let i = 0;
    const interval = setInterval(() => {
      if (i < text.length) {
        setDisplayed(text.slice(0, i + 1));
        i++;
      } else {
        setDone(true);
        clearInterval(interval);
      }
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed]);

  return (
    <span>
      {displayed}
      {!done && <span className="animate-pulse text-indigo-400">|</span>}
    </span>
  );
}

// ── Module demo icons ──────────────────────────────────

const moduleIcons: Record<string, React.ElementType> = {
  assistant: MessageSquare,
  monitor: AlertTriangle,
  memory: Brain,
  review: FileSearch,
  docs: FileText,
  rules: Scale,
  codegen: Code2,
  impact: GitCompare,
  incidents: Siren,
  executive: LineChart,
  security: Shield,
};

// ── Demo simulations ───────────────────────────────────

function DemoAssistant() {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 font-mono text-sm">
      <div className="mb-3 flex items-center gap-2 text-slate-500">
        <MessageSquare className="h-4 w-4" />
        <span>Chat — Assistente de Suporte</span>
      </div>
      <div className="space-y-3">
        <div className="rounded-lg bg-indigo-500/10 border border-indigo-500/20 px-3 py-2 text-slate-300">
          Como funciona a autenticação JWT no módulo de login?
        </div>
        <div className="rounded-lg bg-white/[0.04] border border-white/[0.06] px-3 py-2 text-slate-300">
          <Typewriter
            text="O sistema usa python-jose para gerar tokens JWT. O fluxo: 1) Login valida credenciais com bcrypt, 2) Gera access_token (15min) + refresh_token (7d), 3) Middleware extrai sub do payload."
            speed={20}
          />
          <div className="mt-2 flex gap-2">
            <span className="rounded bg-indigo-500/20 px-2 py-0.5 text-[10px] text-indigo-300">
              app/core/auth.py:42
            </span>
            <span className="rounded bg-indigo-500/20 px-2 py-0.5 text-[10px] text-indigo-300">
              app/api/deps.py:30
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function DemoMonitor() {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 text-sm">
      <div className="mb-3 flex items-center gap-2 text-slate-500">
        <AlertTriangle className="h-4 w-4" />
        <span>Alerta — Monitor de Erros</span>
      </div>
      <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="font-semibold text-red-300">NullPointerException em PaymentService</span>
          <span className="rounded bg-red-500/20 px-2 py-0.5 text-[10px] text-red-300">CRITICAL</span>
        </div>
        <p className="text-slate-400 text-xs mb-2">
          O método processPayment() tenta acessar user.subscription que pode ser null quando o usuário não tem plano ativo.
        </p>
        <div className="flex gap-2 text-[10px]">
          <span className="rounded bg-white/[0.06] px-2 py-0.5 text-slate-400">Sugestão: adicionar null check na linha 87</span>
        </div>
      </div>
    </div>
  );
}

function DemoReview() {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 text-sm font-mono">
      <div className="mb-3 flex items-center gap-2 text-slate-500 font-sans">
        <FileSearch className="h-4 w-4" />
        <span>Revisão — PR #142</span>
        <span className="ml-auto rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] text-emerald-300">Score: 82/100</span>
      </div>
      <div className="space-y-2">
        {[
          { cat: "Bug", color: "red", msg: "Race condition em updateBalance() — usar transaction" },
          { cat: "Segurança", color: "amber", msg: "SQL injection via user input na query L.45" },
          { cat: "Performance", color: "blue", msg: "N+1 query no loop de notificações" },
        ].map((f) => (
          <div key={f.cat} className={`flex items-start gap-2 rounded-lg bg-${f.color}-500/5 border border-${f.color}-500/20 px-3 py-2`}
            style={{ backgroundColor: `rgb(var(--${f.color}) / 0.05)` }}
          >
            <span className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold text-${f.color}-300 bg-${f.color}-500/20`}
              style={{
                color: f.color === "red" ? "#fca5a5" : f.color === "amber" ? "#fcd34d" : "#93c5fd",
                backgroundColor: f.color === "red" ? "rgba(239,68,68,0.2)" : f.color === "amber" ? "rgba(245,158,11,0.2)" : "rgba(59,130,246,0.2)",
              }}
            >
              {f.cat}
            </span>
            <span className="text-slate-300 text-xs">{f.msg}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DemoRules() {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 text-sm">
      <div className="mb-3 flex items-center gap-2 text-slate-500">
        <Scale className="h-4 w-4" />
        <span>Regras de Negócio Extraídas</span>
      </div>
      <div className="space-y-2">
        {[
          { rule: "Pedido acima de R$500 exige aprovação do gestor", complexity: "Média" },
          { rule: "Usuário com 3 tentativas de login é bloqueado por 15min", complexity: "Baixa" },
          { rule: "Desconto máximo de 30% sem cupom especial", complexity: "Alta" },
        ].map((r) => (
          <div key={r.rule} className="flex items-start justify-between gap-3 rounded-lg bg-white/[0.04] border border-white/[0.06] px-3 py-2">
            <span className="text-slate-300 text-xs">{r.rule}</span>
            <span className={`shrink-0 rounded px-2 py-0.5 text-[10px] ${
              r.complexity === "Alta" ? "bg-red-500/20 text-red-300" :
              r.complexity === "Média" ? "bg-amber-500/20 text-amber-300" :
              "bg-emerald-500/20 text-emerald-300"
            }`}>{r.complexity}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DemoGeneric({ icon: Icon, title, items }: { icon: React.ElementType; title: string; items: string[] }) {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 text-sm">
      <div className="mb-3 flex items-center gap-2 text-slate-500">
        <Icon className="h-4 w-4" />
        <span>{title}</span>
      </div>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item} className="flex items-center gap-2 rounded-lg bg-white/[0.04] border border-white/[0.06] px-3 py-2">
            <div className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
            <span className="text-slate-300 text-xs">{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const demoComponents: Record<string, React.ReactNode> = {
  assistant: <DemoAssistant />,
  monitor: <DemoMonitor />,
  review: <DemoReview />,
  rules: <DemoRules />,
  memory: <DemoGeneric icon={Brain} title="Memória Técnica" items={["PR #138: Migração para bcrypt — decisão por incompatibilidade passlib", "Commit a3f2e: Refatoração do search — RRF fusion k=60", "ADR-005: Escolha de pgvector sobre Pinecone por custo"]} />,
  docs: <DemoGeneric icon={FileText} title="Documentação Gerada" items={["auth.py — Sistema de autenticação JWT (atualizado 2h atrás)", "search.py — Busca híbrida com RRF fusion (3 seções)", "ingestor.py — Pipeline de indexação de repositórios"]} />,
  codegen: <DemoGeneric icon={Code2} title="Geração de Código" items={["Endpoint CRUD seguindo padrão do projeto (deps.py pattern)", "Teste unitário com mock_session e fixtures do conftest", "Migration script para nova tabela (padrão scripts/)"]} />,
  impact: <DemoGeneric icon={GitCompare} title="Análise de Impacto" items={["Alterar User.role afeta: deps.py, admin.py, 12 testes", "Risco: ALTO — 3 middlewares dependem deste campo", "Sugestão: migração gradual com feature flag"]} />,
  incidents: <DemoGeneric icon={Siren} title="War Room — Incidente #7" items={["Timeline: 14:32 alerta → 14:35 declarado → 14:42 hipótese IA", "Hipótese IA: Connection pool esgotado por query sem LIMIT", "Similar: Incidente #3 (mesma causa, resolvido em 18min)"]} />,
  executive: <DemoGeneric icon={LineChart} title="Painel Executivo — Semana 10" items={["Security Score: 87 (+5 vs semana anterior)", "Erros detectados: 23 (↓ 31% vs média)", "Tempo médio resolução: 2.4h (↓ 0.8h)"]} />,
  security: <DemoGeneric icon={Shield} title="Scan de Segurança" items={["SQL Injection em query_builder.py:45 — CRITICAL", "XSS potencial em template não-escaped — HIGH", "Dependência com CVE-2024-1234 — MEDIUM"]} />,
};

// ── FAQ Accordion ──────────────────────────────────────

function FAQItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-b border-white/[0.06]">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between py-5 text-left"
      >
        <span className="text-sm font-medium text-white pr-4">{question}</span>
        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="shrink-0"
        >
          <ChevronDown className="h-4 w-4 text-slate-400" />
        </motion.div>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <p className="pb-5 text-sm leading-relaxed text-slate-400">{answer}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Pain point card ────────────────────────────────────

function PainCard({
  title,
  description,
  solution,
  index,
}: {
  title: string;
  description: string;
  solution: string;
  index: number;
}) {
  return (
    <FadeIn delay={index * 0.08}>
      <div className="group relative rounded-2xl border border-white/[0.08] bg-white/[0.03] p-6 backdrop-blur-sm transition-all duration-300 hover:border-indigo-500/30 hover:bg-white/[0.06]">
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-indigo-500/[0.05] to-purple-500/[0.05] opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
        <div className="relative">
          <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-lg bg-red-500/10 ring-1 ring-red-500/20">
            <AlertTriangle className="h-4 w-4 text-red-400" />
          </div>
          <h3 className="mb-2 text-sm font-semibold text-white">{title}</h3>
          <p className="mb-4 text-xs leading-relaxed text-slate-500">{description}</p>
          <div className="flex items-center gap-2 text-xs font-medium text-indigo-400">
            <ArrowRight className="h-3 w-3" />
            {solution}
          </div>
        </div>
      </div>
    </FadeIn>
  );
}

// ── Main page content ──────────────────────────────────

function LandingContent() {
  const { t, locale, toggleLocale } = useI18n();
  const [activeModule, setActiveModule] = useState("assistant");
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const appUrl = "https://memora-system.vercel.app/auth/signin";

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-slate-200 overflow-hidden">
      {/* ── Nav ─────────────────────────────────── */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled
            ? "border-b border-white/[0.06] bg-[#0a0a0a]/80 backdrop-blur-xl"
            : "bg-transparent"
        }`}
      >
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Image src="/memora-logo.png" alt="Memora" width={180} height={40} className="h-8 w-auto" />
          </div>

          <div className="hidden md:flex items-center gap-8">
            <a href="#demo" className="text-sm text-slate-400 transition-colors hover:text-white">
              {t.nav.product}
            </a>
            <a href="#precos" className="text-sm text-slate-400 transition-colors hover:text-white">
              {t.nav.pricing}
            </a>
            <a href="#precos" className="text-sm text-slate-400 transition-colors hover:text-white">
              {t.nav.enterprise}
            </a>
            <a href="#precos" className="text-sm text-slate-400 transition-colors hover:text-white">
              {t.nav.customer}
            </a>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleLocale}
              className="flex items-center gap-1.5 rounded-lg border border-white/[0.08] px-2.5 py-1.5 text-xs font-medium text-slate-400 transition-colors hover:bg-white/[0.06] hover:text-white"
            >
              <Globe className="h-3.5 w-3.5" />
              {locale === "pt" ? "EN" : "PT"}
            </button>
            <Link
              href={appUrl}
              className="rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-indigo-500/20 transition-all hover:shadow-indigo-500/30 hover:scale-[1.02]"
            >
              {t.nav.cta}
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────── */}
      <section className="relative pt-32 md:pt-40">
        {/* Gradient orbs */}
        <div className="pointer-events-none absolute -top-40 left-1/2 h-[600px] w-[800px] -translate-x-1/2 rounded-full bg-gradient-to-br from-indigo-600/20 via-purple-600/10 to-transparent blur-3xl" />
        <div className="pointer-events-none absolute right-0 top-20 h-[400px] w-[400px] rounded-full bg-purple-600/10 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-6 pb-20 md:pb-28">
          <div className="flex flex-col items-center text-center">
            {/* Badge */}
            <FadeIn>
              <motion.span
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.5, repeat: Infinity, repeatType: "reverse", repeatDelay: 3 }}
                className="mb-6 inline-flex items-center rounded-full border border-indigo-400/20 bg-indigo-500/10 px-4 py-1.5 text-xs font-medium text-indigo-300"
              >
                <Zap className="mr-1.5 h-3 w-3" />
                {t.hero.badge}
              </motion.span>
            </FadeIn>

            {/* Headline */}
            <FadeIn delay={0.1}>
              <h1 className="max-w-4xl text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-7xl">
                {t.hero.headline}
              </h1>
            </FadeIn>

            <FadeIn delay={0.2}>
              <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-400">
                {t.hero.subheadline}
              </p>
            </FadeIn>

            {/* CTAs */}
            <FadeIn delay={0.3}>
              <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
                <Link
                  href={appUrl}
                  className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-7 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all duration-200 hover:shadow-indigo-500/40 hover:scale-[1.03]"
                >
                  {t.hero.ctaPrimary}
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <a
                  href="#demo"
                  className="inline-flex items-center gap-2 rounded-xl border border-white/[0.1] px-7 py-3.5 text-sm font-medium text-slate-300 transition-colors hover:bg-white/[0.06] hover:text-white"
                >
                  {t.hero.ctaSecondary}
                </a>
              </div>
            </FadeIn>

            {/* Dashboard mockup */}
            <FadeIn delay={0.4} className="mt-16 w-full max-w-4xl">
              <div className="relative rounded-2xl border border-white/[0.08] bg-white/[0.03] p-1 shadow-2xl shadow-indigo-500/10">
                {/* Browser chrome */}
                <div className="flex items-center gap-2 rounded-t-xl bg-white/[0.04] px-4 py-3 border-b border-white/[0.06]">
                  <div className="flex gap-1.5">
                    <div className="h-2.5 w-2.5 rounded-full bg-red-500/40" />
                    <div className="h-2.5 w-2.5 rounded-full bg-amber-500/40" />
                    <div className="h-2.5 w-2.5 rounded-full bg-emerald-500/40" />
                  </div>
                  <div className="ml-3 flex-1 rounded-md bg-white/[0.06] px-3 py-1 text-[10px] text-slate-500">
                    memora-system.vercel.app/dashboard
                  </div>
                </div>
                {/* Mock content */}
                <div className="p-6 space-y-4">
                  <div className="flex gap-4">
                    <div className="w-48 space-y-3">
                      {["Repositórios", "Monitor", "Memória", "Revisão", "Regras"].map((item) => (
                        <div key={item} className="rounded-lg bg-white/[0.04] px-3 py-2 text-xs text-slate-400">
                          {item}
                        </div>
                      ))}
                    </div>
                    <div className="flex-1">
                      <DemoAssistant />
                    </div>
                  </div>
                </div>
              </div>

              {/* Floating metrics */}
              <div className="mt-8 flex flex-wrap items-center justify-center gap-4 md:gap-6">
                {[t.hero.metric1, t.hero.metric2, t.hero.metric3].map((metric, i) => (
                  <motion.div
                    key={metric}
                    animate={{ y: [0, -6, 0] }}
                    transition={{ duration: 3, delay: i * 0.5, repeat: Infinity, ease: "easeInOut" }}
                    className="rounded-full border border-white/[0.08] bg-white/[0.04] px-4 py-2 text-xs font-medium text-slate-300 backdrop-blur-sm"
                  >
                    {metric}
                  </motion.div>
                ))}
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* ── Pain Points ─────────────────────────── */}
      <section className="relative border-t border-white/[0.06]">
        <div className="pointer-events-none absolute left-0 top-0 h-[300px] w-[300px] rounded-full bg-red-600/5 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-28">
          <FadeIn>
            <h2 className="mb-4 text-center text-3xl font-bold tracking-tight text-white">
              {t.pains.title}
            </h2>
          </FadeIn>

          <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {t.pains.items.map((pain, i) => (
              <PainCard key={i} index={i} title={pain.title} description={pain.description} solution={pain.solution} />
            ))}
          </div>
        </div>
      </section>

      {/* ── Demo Interativo ─────────────────────── */}
      <section id="demo" className="relative border-t border-white/[0.06] bg-white/[0.02]">
        <div className="pointer-events-none absolute right-0 top-0 h-[400px] w-[400px] rounded-full bg-indigo-600/10 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-28">
          <FadeIn>
            <h2 className="mb-2 text-center text-3xl font-bold tracking-tight text-white">
              {t.demo.title}
            </h2>
            <p className="mx-auto mb-12 max-w-2xl text-center text-slate-400">
              {t.demo.subtitle}
            </p>
          </FadeIn>

          <FadeIn delay={0.1}>
            {/* Tabs */}
            <div className="mb-8 flex flex-wrap justify-center gap-2">
              {t.demo.modules.map((mod) => {
                const Icon = moduleIcons[mod.id] || MessageSquare;
                return (
                  <button
                    key={mod.id}
                    onClick={() => setActiveModule(mod.id)}
                    className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-all ${
                      activeModule === mod.id
                        ? "bg-indigo-500/20 text-indigo-300 ring-1 ring-indigo-500/30"
                        : "text-slate-400 hover:bg-white/[0.06] hover:text-white"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {mod.label}
                  </button>
                );
              })}
            </div>

            {/* Demo panel */}
            <div className="grid gap-8 lg:grid-cols-2 items-start">
              {/* Description */}
              <AnimatePresence mode="wait">
                {t.demo.modules
                  .filter((m) => m.id === activeModule)
                  .map((mod) => (
                    <motion.div
                      key={mod.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      transition={{ duration: 0.3 }}
                      className="flex flex-col justify-center"
                    >
                      <div className="flex items-center gap-3 mb-4">
                        {(() => {
                          const Icon = moduleIcons[mod.id] || MessageSquare;
                          return (
                            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 ring-1 ring-white/[0.08]">
                              <Icon className="h-5 w-5 text-indigo-300" />
                            </div>
                          );
                        })()}
                        <h3 className="text-xl font-bold text-white">{mod.title}</h3>
                      </div>
                      <p className="text-sm leading-relaxed text-slate-400">{mod.description}</p>
                    </motion.div>
                  ))}
              </AnimatePresence>

              {/* Visual simulation */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeModule}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ duration: 0.3 }}
                >
                  {demoComponents[activeModule]}
                </motion.div>
              </AnimatePresence>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── Pricing ─────────────────────────────── */}
      <section id="precos" className="relative border-t border-white/[0.06]">
        <div className="pointer-events-none absolute right-0 top-0 h-[400px] w-[400px] rounded-full bg-indigo-600/10 blur-3xl" />
        <div className="pointer-events-none absolute left-0 bottom-0 h-[300px] w-[300px] rounded-full bg-purple-600/10 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-28">
          <FadeIn>
            <h2 className="mb-2 text-center text-3xl font-bold tracking-tight text-white">
              {t.pricing.title}
            </h2>
            <p className="mx-auto mb-14 max-w-2xl text-center text-slate-400">
              {t.pricing.subtitle}
            </p>
          </FadeIn>

          <div className="grid gap-6 lg:grid-cols-3">
            {/* PRO */}
            <FadeIn delay={0}>
              <div className="relative rounded-2xl border-2 border-indigo-500/40 bg-white/[0.04] p-8 backdrop-blur-sm h-full flex flex-col">
                <div className="absolute -top-3 left-6">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 px-3 py-1 text-xs font-semibold text-white shadow-lg shadow-indigo-500/25">
                    <Crown className="h-3 w-3" />
                    {t.pricing.plans.pro.badge}
                  </span>
                </div>

                <div className="mt-4 flex flex-col gap-6 flex-1">
                  <div>
                    <h3 className="text-xl font-bold text-white">{t.pricing.plans.pro.name}</h3>
                    <p className="mt-1 text-sm text-slate-400">{t.pricing.plans.pro.description}</p>
                  </div>

                  <div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-bold text-white">{t.pricing.plans.pro.price}</span>
                      <span className="text-sm text-slate-400">{t.pricing.plans.pro.period}</span>
                    </div>
                    <p className="mt-2 text-xs text-slate-500">{t.pricing.plans.pro.roi}</p>
                  </div>

                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-2.5">
                    <p className="text-sm font-medium text-emerald-300">{t.pricing.plans.pro.note}</p>
                  </div>

                  <ul className="flex flex-col gap-3">
                    {t.pricing.plans.pro.features.map((f) => (
                      <li key={f} className="flex items-start gap-2.5 text-sm text-slate-300">
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
                        {f}
                      </li>
                    ))}
                  </ul>

                  <Link
                    href={appUrl}
                    className="mt-auto inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all duration-200 hover:shadow-indigo-500/40 hover:scale-[1.03]"
                  >
                    {t.pricing.plans.pro.cta}
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
              </div>
            </FadeIn>

            {/* Enterprise */}
            <FadeIn delay={0.1}>
              <div className="relative rounded-2xl border border-white/[0.08] bg-white/[0.03] p-8 backdrop-blur-sm h-full flex flex-col">
                <div className="absolute -top-3 left-6">
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.15] bg-white/[0.08] px-3 py-1 text-xs font-semibold text-slate-200">
                    <ShieldCheck className="h-3 w-3" />
                    {t.pricing.plans.enterprise.badge}
                  </span>
                </div>

                <div className="mt-4 flex flex-col gap-6 flex-1">
                  <div>
                    <h3 className="text-xl font-bold text-white">{t.pricing.plans.enterprise.name}</h3>
                    <p className="mt-1 text-sm text-slate-400">{t.pricing.plans.enterprise.description}</p>
                  </div>

                  <div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-bold text-white">{t.pricing.plans.enterprise.price}</span>
                      <span className="text-sm text-slate-400">{t.pricing.plans.enterprise.period}</span>
                    </div>
                  </div>

                  <ul className="flex flex-col gap-3">
                    {t.pricing.plans.enterprise.features.map((f) => (
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
                    {t.pricing.plans.enterprise.cta}
                    <Building2 className="h-4 w-4" />
                  </Link>
                </div>
              </div>
            </FadeIn>

            {/* Customer */}
            <FadeIn delay={0.2}>
              <div className="relative rounded-2xl border border-white/[0.08] bg-white/[0.03] p-8 backdrop-blur-sm h-full flex flex-col">
                <div className="absolute -top-3 left-6">
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/20 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-300">
                    <Sparkles className="h-3 w-3" />
                    {t.pricing.plans.customer.badge}
                  </span>
                </div>

                <div className="mt-4 flex flex-col gap-6 flex-1">
                  <div>
                    <h3 className="text-xl font-bold text-white">{t.pricing.plans.customer.name}</h3>
                    <p className="mt-1 text-sm text-slate-400">{t.pricing.plans.customer.description}</p>
                  </div>

                  <div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-bold text-white">{t.pricing.plans.customer.price}</span>
                    </div>
                  </div>

                  <ul className="flex flex-col gap-3">
                    {t.pricing.plans.customer.features.map((f) => (
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
                    {t.pricing.plans.customer.cta}
                    <Sparkles className="h-4 w-4" />
                  </Link>
                </div>
              </div>
            </FadeIn>
          </div>

          {/* Early adopter note */}
          <FadeIn delay={0.3}>
            <div className="mt-8 flex items-center justify-center gap-2 text-center">
              <Star className="h-4 w-4 text-amber-400/70" />
              <p className="text-sm text-slate-500">
                {t.pricing.earlyAdopter}
              </p>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── FAQ ──────────────────────────────────── */}
      <section className="relative border-t border-white/[0.06] bg-white/[0.02]">
        <div className="relative mx-auto max-w-3xl px-6 py-20 md:py-28">
          <FadeIn>
            <h2 className="mb-12 text-center text-3xl font-bold tracking-tight text-white">
              {t.faq.title}
            </h2>
          </FadeIn>

          <FadeIn delay={0.1}>
            <div className="divide-y divide-white/[0.06] rounded-2xl border border-white/[0.08] bg-white/[0.03] px-6 backdrop-blur-sm">
              {t.faq.items.map((item, i) => (
                <FAQItem key={i} question={item.q} answer={item.a} />
              ))}
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────── */}
      <section className="relative border-t border-white/[0.06]">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-indigo-600/5 to-transparent" />

        <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-28 text-center">
          <FadeIn>
            <h2 className="mb-4 text-3xl font-bold tracking-tight text-white sm:text-4xl">
              {t.cta.headline}
            </h2>
            <p className="mx-auto mb-10 max-w-xl text-lg text-slate-400">
              {t.cta.subheadline}
            </p>

            <Link
              href={appUrl}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-8 py-4 text-base font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all duration-200 hover:shadow-indigo-500/40 hover:scale-[1.03]"
            >
              {t.cta.button}
              <ArrowRight className="h-4 w-4" />
            </Link>
          </FadeIn>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────── */}
      <footer className="border-t border-white/[0.06]">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
            <div className="flex flex-col items-center gap-2 sm:items-start">
              <div className="flex items-center gap-2">
                <Image src="/memora-logo.png" alt="Memora" width={120} height={28} className="h-6 w-auto" />
              </div>
              <span className="text-xs text-slate-500">{t.footer.tagline}</span>
            </div>

            <div className="flex items-center gap-6 text-sm text-slate-500">
              <a href="#demo" className="transition-colors hover:text-slate-300">{t.footer.product}</a>
              <a href="#precos" className="transition-colors hover:text-slate-300">{t.footer.pricing}</a>
              <button onClick={toggleLocale} className="flex items-center gap-1 transition-colors hover:text-slate-300">
                <Globe className="h-3.5 w-3.5" />
                {locale === "pt" ? "EN" : "PT"}
              </button>
            </div>
          </div>

          <div className="mt-6 border-t border-white/[0.06] pt-6 text-center">
            <p className="text-xs text-slate-600">{t.footer.rights}</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

// ── Export with I18n wrapper ───────────────────────────

export default function LandingPage() {
  return (
    <I18nProvider>
      <LandingContent />
    </I18nProvider>
  );
}
