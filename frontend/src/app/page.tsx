"use client";

import Link from "next/link";
import Image from "next/image";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRight,
  Check,
  ChevronDown,
  Globe,
  MessageSquare,
  Brain,
  FileText,
  GitCompare,
  Siren,
  AlertTriangle,
  LineChart,
  Building2,
  Crown,
  Code2,
  Sparkles,
  Users,
  HeadphonesIcon,
  ShieldCheck,
  Boxes,
  Menu,
  X,
  GitBranch,
  Cpu,
  Database,
  HelpCircle,
} from "lucide-react";
import { I18nProvider, useI18n } from "@/lib/i18n";

// ── Animation wrapper ──────────────────────────────────

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
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.6, delay, ease: [0.21, 0.47, 0.32, 0.98] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ── FAQ Accordion ──────────────────────────────────────

function FAQItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-b border-white/[0.06] last:border-0">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between py-5 text-left"
      >
        <span className="text-[15px] font-medium text-white pr-8">{question}</span>
        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="shrink-0"
        >
          <ChevronDown className="h-4 w-4 text-slate-500" />
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

// ── Module icons mapping ────────────────────────────────

const moduleIcons = [
  MessageSquare,
  Brain,
  FileText,
  GitCompare,
  Siren,
  AlertTriangle,
  LineChart,
  ShieldCheck,
];

// ── Use case icons mapping ──────────────────────────────

const useCaseIcons = [Code2, HeadphonesIcon, ShieldCheck, Siren, Boxes];

// ── How it works step icons ─────────────────────────────

const stepIcons = [GitBranch, Cpu, Database, HelpCircle];

// ── Main landing content ────────────────────────────────

function LandingContent() {
  const { t, locale, toggleLocale } = useI18n();
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const appUrl = "https://memora-system.vercel.app/auth/signin";

  return (
    <div className="min-h-screen bg-[#09090b] text-slate-200 antialiased">
      {/* ─── Nav ───────────────────────────────── */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled
            ? "border-b border-white/[0.06] bg-[#09090b]/80 backdrop-blur-xl"
            : "bg-transparent"
        }`}
      >
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Image src="/memora-logo.png" alt="Memora" width={140} height={32} className="h-7 w-auto" />

          <div className="hidden md:flex items-center gap-8">
            <a href="#how-it-works" className="text-sm text-slate-400 transition-colors hover:text-white">
              {t.nav.product}
            </a>
            <a href="#pricing" className="text-sm text-slate-400 transition-colors hover:text-white">
              {t.nav.pricing}
            </a>
            <a href="#faq" className="text-sm text-slate-400 transition-colors hover:text-white">
              {t.nav.docs}
            </a>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleLocale}
              className="hidden md:flex items-center gap-1.5 rounded-lg border border-white/[0.08] px-2.5 py-1.5 text-xs font-medium text-slate-400 transition-colors hover:bg-white/[0.06] hover:text-white"
            >
              <Globe className="h-3.5 w-3.5" />
              {locale === "pt" ? "EN" : "PT"}
            </button>
            <Link
              href={appUrl}
              className="hidden md:inline-flex rounded-lg bg-white px-4 py-2 text-sm font-semibold text-[#09090b] transition-all hover:bg-slate-200"
            >
              {t.nav.cta}
            </Link>
            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-slate-400 hover:bg-white/[0.06]"
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="md:hidden overflow-hidden border-t border-white/[0.06] bg-[#09090b]/95 backdrop-blur-xl"
            >
              <div className="flex flex-col gap-1 px-6 py-4">
                <a href="#how-it-works" onClick={() => setMobileMenuOpen(false)} className="py-2.5 text-sm text-slate-300 hover:text-white">
                  {t.nav.product}
                </a>
                <a href="#pricing" onClick={() => setMobileMenuOpen(false)} className="py-2.5 text-sm text-slate-300 hover:text-white">
                  {t.nav.pricing}
                </a>
                <a href="#faq" onClick={() => setMobileMenuOpen(false)} className="py-2.5 text-sm text-slate-300 hover:text-white">
                  {t.nav.docs}
                </a>
                <div className="flex items-center gap-3 pt-3 border-t border-white/[0.06] mt-2">
                  <button
                    onClick={toggleLocale}
                    className="flex items-center gap-1.5 rounded-lg border border-white/[0.08] px-2.5 py-1.5 text-xs font-medium text-slate-400"
                  >
                    <Globe className="h-3.5 w-3.5" />
                    {locale === "pt" ? "EN" : "PT"}
                  </button>
                  <Link href={appUrl} className="flex-1 text-center rounded-lg bg-white px-4 py-2 text-sm font-semibold text-[#09090b]">
                    {t.nav.cta}
                  </Link>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      {/* ─── Hero ──────────────────────────────── */}
      <section className="relative pt-32 pb-16 md:pt-44 md:pb-28 overflow-hidden">
        {/* Gradient background */}
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 h-[600px] w-[900px] rounded-full bg-gradient-to-br from-violet-600/15 via-indigo-600/10 to-transparent blur-3xl" />
          <div className="absolute top-40 right-0 h-[400px] w-[400px] rounded-full bg-purple-600/8 blur-3xl" />
        </div>

        <div className="relative mx-auto max-w-5xl px-6 text-center">
          <FadeIn>
            <h1 className="text-5xl font-bold tracking-tight text-white sm:text-6xl lg:text-[4.5rem] lg:leading-[1.08] whitespace-pre-line">
              {t.hero.headline}
            </h1>
          </FadeIn>

          <FadeIn delay={0.1}>
            <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-400 md:text-xl md:leading-relaxed">
              {t.hero.subheadline}
            </p>
          </FadeIn>

          <FadeIn delay={0.2}>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href={appUrl}
                className="group inline-flex items-center gap-2.5 rounded-xl bg-white px-8 py-3.5 text-[15px] font-semibold text-[#09090b] shadow-lg shadow-white/10 transition-all hover:bg-slate-100 hover:shadow-white/20 hover:scale-[1.02]"
              >
                {t.hero.ctaPrimary}
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
              <a
                href="#how-it-works"
                className="inline-flex items-center gap-2 rounded-xl border border-white/[0.1] px-8 py-3.5 text-[15px] font-medium text-slate-300 transition-colors hover:bg-white/[0.06] hover:text-white"
              >
                {t.hero.ctaSecondary}
              </a>
            </div>
            <p className="mt-4 text-xs text-slate-600 text-center">
              {locale === "pt" ? "Sem cartão de crédito. Cancele quando quiser." : "No credit card required. Cancel anytime."}
            </p>
          </FadeIn>

          {/* Dashboard mockup */}
          <FadeIn delay={0.35} className="mt-20">
            <div className="relative mx-auto max-w-4xl">
              {/* Glow behind the mockup */}
              <div className="absolute -inset-px rounded-2xl bg-gradient-to-b from-violet-500/20 via-transparent to-transparent blur-sm" />
              <div className="relative rounded-2xl border border-white/[0.08] bg-white/[0.02] p-1 shadow-2xl shadow-violet-500/5">
                <div className="flex items-center gap-2 rounded-t-xl bg-white/[0.03] px-4 py-3 border-b border-white/[0.06]">
                  <div className="flex gap-1.5">
                    <div className="h-2.5 w-2.5 rounded-full bg-red-500/30" />
                    <div className="h-2.5 w-2.5 rounded-full bg-amber-500/30" />
                    <div className="h-2.5 w-2.5 rounded-full bg-emerald-500/30" />
                  </div>
                  <div className="ml-3 flex-1 rounded-md bg-white/[0.04] px-3 py-1 text-[11px] text-slate-600">
                    memora.app/dashboard
                  </div>
                </div>
                <div className="p-6">
                  <div className="flex gap-4">
                    <div className="hidden sm:block w-44 space-y-2">
                      {["Chat", "Monitor", "Memory", "Reviews", "Incidents"].map((item, i) => (
                        <div
                          key={item}
                          className={`rounded-lg px-3 py-2 text-xs ${
                            i === 0
                              ? "bg-violet-500/10 text-violet-300 border border-violet-500/20"
                              : "text-slate-500 border border-transparent"
                          }`}
                        >
                          {item}
                        </div>
                      ))}
                    </div>
                    <div className="flex-1 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 font-mono text-sm">
                      <div className="mb-3 flex items-center gap-2 text-slate-500 text-xs">
                        <MessageSquare className="h-3.5 w-3.5" />
                        <span>Assistant</span>
                      </div>
                      <div className="space-y-3">
                        <div className="rounded-lg bg-violet-500/10 border border-violet-500/20 px-3 py-2 text-slate-300 text-xs">
                          How does JWT authentication work in the login module?
                        </div>
                        <div className="rounded-lg bg-white/[0.03] border border-white/[0.06] px-3 py-2 text-slate-400 text-xs leading-relaxed">
                          The system uses python-jose to generate JWT tokens. Flow: 1) Login validates credentials with bcrypt, 2) Generates access_token (15min) + refresh_token (7d), 3) Middleware extracts sub from payload.
                          <div className="mt-2 flex gap-2">
                            <span className="rounded bg-violet-500/15 px-2 py-0.5 text-[10px] text-violet-300">
                              app/core/auth.py:42
                            </span>
                            <span className="rounded bg-violet-500/15 px-2 py-0.5 text-[10px] text-violet-300">
                              app/api/deps.py:30
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              {/* Bottom fade */}
              <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-[#09090b] to-transparent rounded-b-2xl" />
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ─── Social Proof ──────────────────────── */}
      <section className="relative border-t border-white/[0.04]">
        <div className="mx-auto max-w-5xl px-6 py-12">
          <FadeIn>
            <p className="text-center text-xs font-medium uppercase tracking-widest text-slate-600 mb-8">
              {locale === "pt" ? "Construído para times de software que valorizam conhecimento" : "Built for software teams that value knowledge"}
            </p>
            <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-4">
              {[
                { label: locale === "pt" ? "Software houses" : "Software houses", icon: Code2 },
                { label: locale === "pt" ? "Startups SaaS" : "SaaS startups", icon: Sparkles },
                { label: locale === "pt" ? "Times de engenharia" : "Engineering teams", icon: Users },
                { label: locale === "pt" ? "Suporte técnico" : "Technical support", icon: HeadphonesIcon },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-2 text-slate-500">
                  <item.icon className="h-4 w-4" />
                  <span className="text-sm">{item.label}</span>
                </div>
              ))}
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ─── Problem ───────────────────────────── */}
      <section className="relative border-t border-white/[0.06]">
        <div className="mx-auto max-w-5xl px-6 py-24 md:py-36">
          <FadeIn>
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl lg:text-[2.75rem] max-w-2xl">
              {t.problem.title}
            </h2>
            <p className="mt-4 max-w-2xl text-lg text-slate-500">
              {t.problem.subtitle}
            </p>
          </FadeIn>

          <div className="mt-16 grid gap-4 sm:grid-cols-2 lg:grid-cols-12">
            {t.problem.items.map((item, i) => {
              // 5 items: first row 3 (span-4 each), second row 2 (span-6 each)
              const isSecondRow = i >= 3;
              return (
                <FadeIn key={i} delay={i * 0.06} className={`${isSecondRow ? "lg:col-span-6" : "lg:col-span-4"}`}>
                  <div className="group h-full rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 transition-all duration-300 hover:border-red-500/15 hover:bg-white/[0.04]">
                    <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-red-500/10 ring-1 ring-red-500/10">
                      <div className="h-2 w-2 rounded-full bg-red-400" />
                    </div>
                    <h3 className="mb-2 text-[15px] font-semibold text-white">{item.title}</h3>
                    <p className="text-sm leading-relaxed text-slate-500">{item.description}</p>
                  </div>
                </FadeIn>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── Solution (visual) ─────────────────── */}
      <section className="relative border-t border-white/[0.06] overflow-hidden">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[700px] rounded-full bg-violet-600/5 blur-3xl" />
        </div>

        <div className="relative mx-auto max-w-5xl px-6 py-20 md:py-28">
          <FadeIn>
            <div className="mx-auto max-w-3xl text-center">
              <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl lg:text-[2.75rem]">
                {t.solution.title}
              </h2>
              <p className="mt-6 text-lg leading-relaxed text-slate-400">
                {t.solution.description}
              </p>
            </div>
          </FadeIn>

          {/* Visual flow: Repo → Memora → Knowledge */}
          <FadeIn delay={0.15}>
            <div className="mt-16 flex flex-col md:flex-row items-center justify-center gap-4 md:gap-0">
              {/* Step 1: Repo */}
              <div className="flex flex-col items-center gap-2">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-white/[0.08] bg-white/[0.03]">
                  <GitBranch className="h-7 w-7 text-slate-400" />
                </div>
                <span className="text-xs font-medium text-slate-500">{locale === "pt" ? "Seu repositório" : "Your repository"}</span>
              </div>

              {/* Arrow */}
              <div className="hidden md:block w-20 h-px bg-gradient-to-r from-white/[0.06] via-violet-500/30 to-white/[0.06]" />
              <div className="md:hidden h-8 w-px bg-gradient-to-b from-white/[0.06] via-violet-500/30 to-white/[0.06]" />

              {/* Step 2: Memora */}
              <div className="flex flex-col items-center gap-2">
                <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500/20 to-indigo-500/20 border border-violet-500/20 shadow-lg shadow-violet-500/10">
                  <Cpu className="h-9 w-9 text-violet-400" />
                </div>
                <span className="text-xs font-semibold text-violet-400">Memora</span>
              </div>

              {/* Arrow */}
              <div className="hidden md:block w-20 h-px bg-gradient-to-r from-white/[0.06] via-violet-500/30 to-white/[0.06]" />
              <div className="md:hidden h-8 w-px bg-gradient-to-b from-white/[0.06] via-violet-500/30 to-white/[0.06]" />

              {/* Step 3: Knowledge */}
              <div className="flex flex-col items-center gap-2">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-white/[0.08] bg-white/[0.03]">
                  <Brain className="h-7 w-7 text-slate-400" />
                </div>
                <span className="text-xs font-medium text-slate-500">{locale === "pt" ? "Conhecimento vivo" : "Living knowledge"}</span>
              </div>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ─── How It Works ──────────────────────── */}
      <section id="how-it-works" className="relative border-t border-white/[0.06]">
        <div className="mx-auto max-w-5xl px-6 py-24 md:py-36">
          <FadeIn>
            <div className="text-center">
              <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                {t.howItWorks.title}
              </h2>
              <p className="mt-4 text-lg text-slate-500">
                {t.howItWorks.subtitle}
              </p>
            </div>
          </FadeIn>

          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {t.howItWorks.steps.map((step, i) => {
              const Icon = stepIcons[i];
              return (
                <FadeIn key={i} delay={i * 0.1}>
                  <div className="relative rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 hover:border-violet-500/15 transition-colors">
                    {/* Step number */}
                    <div className="flex items-center justify-between mb-5">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10 ring-1 ring-violet-500/15">
                        <Icon className="h-5 w-5 text-violet-400" />
                      </div>
                      <span className="text-3xl font-bold text-white/[0.07]">{step.number}</span>
                    </div>
                    <h3 className="text-[15px] font-semibold text-white">{step.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-slate-500">{step.description}</p>

                    {/* Connector line (not on last) */}
                    {i < 3 && (
                      <div className="hidden lg:block absolute top-1/2 -right-3 w-6 h-px bg-white/[0.06]" />
                    )}
                  </div>
                </FadeIn>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── Benefits ──────────────────────────── */}
      <section className="relative border-t border-white/[0.06] bg-white/[0.01]">
        <div className="mx-auto max-w-5xl px-6 py-20 md:py-28">
          <FadeIn>
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl text-center">
              {t.benefits.title}
            </h2>
          </FadeIn>

          <div className="mt-16 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {t.benefits.items.map((item, i) => (
              <FadeIn key={i} delay={i * 0.06}>
                <div className="rounded-xl border border-white/[0.04] bg-white/[0.02] p-5 transition-colors hover:bg-white/[0.04]">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-500/10">
                      <Check className="h-4 w-4 text-violet-400" />
                    </div>
                    <h3 className="text-[15px] font-semibold text-white">{item.title}</h3>
                  </div>
                  <p className="text-sm text-slate-500 pl-11">{item.description}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Mid-page CTA ──────────────────────── */}
      <section className="relative border-t border-white/[0.06]">
        <div className="mx-auto max-w-3xl px-6 py-16 text-center">
          <FadeIn>
            <Link
              href={appUrl}
              className="group inline-flex items-center gap-2.5 rounded-xl bg-white px-8 py-3.5 text-[15px] font-semibold text-[#09090b] shadow-lg shadow-white/10 transition-all hover:bg-slate-100 hover:shadow-white/20 hover:scale-[1.02]"
            >
              {t.hero.ctaPrimary}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <p className="mt-3 text-xs text-slate-600">
              {locale === "pt" ? "7 dias grátis. Sem cartão de crédito." : "7 free days. No credit card."}
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ─── Use Cases (horizontal layout) ────── */}
      <section className="relative border-t border-white/[0.06]">
        <div className="mx-auto max-w-5xl px-6 py-24 md:py-36">
          <FadeIn>
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl text-center">
              {t.useCases.title}
            </h2>
          </FadeIn>

          <div className="mt-16 space-y-3">
            {t.useCases.items.map((item, i) => {
              const Icon = useCaseIcons[i] || Users;
              return (
                <FadeIn key={i} delay={i * 0.06}>
                  <div className="group flex items-center gap-5 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 md:p-6 transition-all duration-300 hover:border-violet-500/15 hover:bg-white/[0.04]">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/10 to-indigo-500/10 ring-1 ring-white/[0.06] group-hover:ring-violet-500/20 transition-colors">
                      <Icon className="h-5 w-5 text-violet-400" />
                    </div>
                    <div>
                      <h3 className="text-[15px] font-semibold text-white">{item.title}</h3>
                      <p className="mt-0.5 text-sm text-slate-500">{item.description}</p>
                    </div>
                  </div>
                </FadeIn>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── Modules (bento grid) ──────────────── */}
      <section className="relative border-t border-white/[0.06] bg-white/[0.01]">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 h-[400px] w-[600px] rounded-full bg-violet-600/5 blur-3xl" />
        </div>

        <div className="relative mx-auto max-w-5xl px-6 py-24 md:py-36">
          <FadeIn>
            <div className="text-center">
              <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                {t.modules.title}
              </h2>
              <p className="mt-4 text-lg text-slate-500">
                {t.modules.subtitle}
              </p>
            </div>
          </FadeIn>

          {/* Bento: 4 top (span-3 each) + 3 bottom (span-4 each) in 12-col grid */}
          <div className="mt-16 grid gap-3 sm:grid-cols-2 lg:grid-cols-12">
            {t.modules.items.map((mod, i) => {
              const Icon = moduleIcons[i] || Sparkles;
              // First row: 4 items (span-3 each = 12). Second row: 3 items (span-4 each = 12)
              const isSecondRow = i >= 4;
              return (
                <FadeIn key={i} delay={i * 0.04} className={isSecondRow ? "lg:col-span-4" : "lg:col-span-3"}>
                  <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 h-full transition-all duration-300 hover:border-violet-500/15 hover:bg-white/[0.04]">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/8 ring-1 ring-violet-500/10 mb-4">
                      <Icon className="h-5 w-5 text-violet-400" />
                    </div>
                    <h3 className="text-[15px] font-semibold text-white">{mod.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{mod.description}</p>
                  </div>
                </FadeIn>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── Pricing ───────────────────────────── */}
      <section id="pricing" className="relative border-t border-white/[0.06]">
        <div className="mx-auto max-w-5xl px-6 py-24 md:py-36">
          <FadeIn>
            <div className="text-center">
              <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                {t.pricing.title}
              </h2>
              <p className="mt-4 text-lg text-slate-500">
                {t.pricing.subtitle}
              </p>
            </div>
          </FadeIn>

          <div className="mt-16 mx-auto grid max-w-3xl gap-6 lg:grid-cols-2">
            {/* Pro */}
            <FadeIn delay={0}>
              <div className="relative rounded-2xl border-2 border-violet-500/30 bg-white/[0.03] p-8 h-full flex flex-col">
                {/* Subtle glow */}
                <div className="absolute -inset-px rounded-2xl bg-gradient-to-b from-violet-500/10 to-transparent opacity-50 -z-10 blur-sm" />
                <div className="absolute -top-3 left-6">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-violet-500 to-indigo-500 px-3 py-1 text-xs font-semibold text-white shadow-lg shadow-violet-500/20">
                    <Crown className="h-3 w-3" />
                    {t.pricing.plans.pro.badge}
                  </span>
                </div>

                <div className="mt-4 flex flex-col gap-6 flex-1">
                  <div>
                    <h3 className="text-xl font-bold text-white">{t.pricing.plans.pro.name}</h3>
                    <p className="mt-1 text-sm text-slate-500">{t.pricing.plans.pro.description}</p>
                  </div>

                  <div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-bold text-white">{t.pricing.plans.pro.price}</span>
                      <span className="text-sm text-slate-500">{t.pricing.plans.pro.period}</span>
                    </div>
                    <p className="mt-2 text-xs text-slate-500">{t.pricing.plans.pro.roi}</p>
                  </div>

                  <ul className="flex flex-col gap-3">
                    {t.pricing.plans.pro.features.map((f) => (
                      <li key={f} className="flex items-start gap-2.5 text-sm text-slate-300">
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-violet-400" />
                        {f}
                      </li>
                    ))}
                  </ul>

                  <div className="mt-auto">
                    <Link
                      href={appUrl}
                      className="group inline-flex w-full items-center justify-center gap-2 rounded-xl bg-white px-6 py-3.5 text-sm font-semibold text-[#09090b] shadow-lg shadow-white/10 transition-all hover:bg-slate-100 hover:shadow-white/20 hover:scale-[1.02]"
                    >
                      {t.pricing.plans.pro.cta}
                      <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                    </Link>
                    <p className="mt-2 text-center text-[11px] text-slate-600">
                      {locale === "pt" ? "Sem cartão. Cancele quando quiser." : "No card required. Cancel anytime."}
                    </p>
                  </div>
                </div>
              </div>
            </FadeIn>

            {/* Enterprise */}
            <FadeIn delay={0.1}>
              <div className="relative rounded-2xl border border-white/[0.08] bg-white/[0.02] p-8 h-full flex flex-col">
                <div className="absolute -top-3 left-6">
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.12] bg-white/[0.06] px-3 py-1 text-xs font-semibold text-slate-300">
                    <Building2 className="h-3 w-3" />
                    {t.pricing.plans.enterprise.badge}
                  </span>
                </div>

                <div className="mt-4 flex flex-col gap-6 flex-1">
                  <div>
                    <h3 className="text-xl font-bold text-white">{t.pricing.plans.enterprise.name}</h3>
                    <p className="mt-1 text-sm text-slate-500">{t.pricing.plans.enterprise.description}</p>
                  </div>

                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold text-white">{t.pricing.plans.enterprise.price}</span>
                    <span className="text-sm text-slate-500">{t.pricing.plans.enterprise.period}</span>
                  </div>

                  <ul className="flex flex-col gap-3">
                    {t.pricing.plans.enterprise.features.map((f) => (
                      <li key={f} className="flex items-start gap-2.5 text-sm text-slate-300">
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-violet-400" />
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
          </div>
        </div>
      </section>

      {/* ─── FAQ ───────────────────────────────── */}
      <section id="faq" className="relative border-t border-white/[0.06] bg-white/[0.01]">
        <div className="mx-auto max-w-2xl px-6 py-20 md:py-28">
          <FadeIn>
            <h2 className="text-3xl font-bold tracking-tight text-white text-center sm:text-4xl">
              {t.faq.title}
            </h2>
          </FadeIn>

          <FadeIn delay={0.1}>
            <div className="mt-12 rounded-2xl border border-white/[0.06] bg-white/[0.02] px-6">
              {t.faq.items.map((item, i) => (
                <FAQItem key={i} question={item.q} answer={item.a} />
              ))}
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ─── Final CTA ─────────────────────────── */}
      <section className="relative border-t border-white/[0.06] overflow-hidden">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 h-[400px] w-[800px] rounded-full bg-gradient-to-b from-violet-600/10 to-transparent blur-3xl" />
        </div>

        <div className="relative mx-auto max-w-3xl px-6 py-24 md:py-36 text-center">
          <FadeIn>
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl lg:text-5xl">
              {t.finalCta.headline}
            </h2>
            <p className="mx-auto mt-6 max-w-xl text-lg text-slate-400">
              {t.finalCta.subheadline}
            </p>

            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href={appUrl}
                className="group inline-flex items-center gap-2.5 rounded-xl bg-white px-8 py-3.5 text-[15px] font-semibold text-[#09090b] shadow-lg shadow-white/10 transition-all hover:bg-slate-100 hover:shadow-white/20 hover:scale-[1.02]"
              >
                {t.finalCta.ctaPrimary}
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
              <a
                href="#pricing"
                className="inline-flex items-center gap-2 rounded-xl border border-white/[0.1] px-8 py-3.5 text-[15px] font-medium text-slate-300 transition-colors hover:bg-white/[0.06] hover:text-white"
              >
                {t.finalCta.ctaSecondary}
              </a>
            </div>
            <p className="mt-4 text-xs text-slate-600 text-center">
              {locale === "pt" ? "Sem cartão de crédito. Cancele quando quiser." : "No credit card required. Cancel anytime."}
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ─── Footer ────────────────────────────── */}
      <footer className="border-t border-white/[0.06]">
        <div className="mx-auto max-w-5xl px-6 py-10">
          <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
            <div className="flex flex-col items-center gap-2 sm:items-start">
              <Image src="/memora-logo.png" alt="Memora" width={100} height={24} className="h-5 w-auto opacity-60" />
              <span className="text-xs text-slate-600">{t.footer.tagline}</span>
            </div>

            <div className="flex items-center gap-6 text-sm text-slate-500">
              <a href="#how-it-works" className="transition-colors hover:text-slate-300">{t.footer.product}</a>
              <a href="#pricing" className="transition-colors hover:text-slate-300">{t.footer.pricing}</a>
              <button onClick={toggleLocale} className="flex items-center gap-1 transition-colors hover:text-slate-300">
                <Globe className="h-3.5 w-3.5" />
                {locale === "pt" ? "EN" : "PT"}
              </button>
            </div>
          </div>

          <div className="mt-8 border-t border-white/[0.04] pt-6 text-center">
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
