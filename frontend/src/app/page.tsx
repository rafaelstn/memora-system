import Image from "next/image";
import Link from "next/link";
import {
  AlertCircle,
  MessageSquare,
  Shield,
  Brain,
  ArrowRight,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

function ChatMockup() {
  return (
    <div className="w-full max-w-md rounded-2xl border border-border bg-card-bg overflow-hidden" style={{ boxShadow: "var(--shadow-lg)" }}>
      <div className="flex items-center gap-2 border-b border-border px-4 py-3 bg-sidebar-bg">
        <div className="h-3 w-3 rounded-full bg-red-400" />
        <div className="h-3 w-3 rounded-full bg-yellow-400" />
        <div className="h-3 w-3 rounded-full bg-green-400" />
        <span className="ml-2 text-xs text-muted">
          Memora Chat
        </span>
      </div>

      <div className="flex flex-col gap-4 p-5">
        <div className="flex items-start gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-white text-sm font-bold">
            U
          </div>
          <div className="rounded-xl bg-hover px-4 py-2.5 text-sm text-foreground">
            Onde fica a lógica de cálculo de frete?
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Image src="/logo.png" alt="Memora" width={32} height={32} className="h-8 w-8 shrink-0 rounded-full" />
          <div className="flex flex-col gap-2 rounded-xl bg-hover px-4 py-2.5 text-sm text-foreground">
            <p>
              A lógica de frete está em{" "}
              <code className="rounded-md bg-accent-surface px-1.5 py-0.5 text-xs font-mono text-accent-text">
                src/services/shipping.ts
              </code>
            </p>
            <div className="rounded-lg bg-background p-3 font-mono text-xs leading-relaxed text-foreground/80 overflow-x-auto">
              <pre>{`export function calcFreight(
  weight: number,
  zone: string
): number {
  const base = ZONE_RATES[zone];
  return base + weight * 0.12;
}`}</pre>
            </div>
            <p className="text-muted text-xs">
              Última alteração: 12/fev por @carlos
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ProblemCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-card-bg p-6 flex flex-col gap-3 hover:border-danger/30 transition-colors" style={{ boxShadow: "var(--shadow-sm)" }}>
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-danger-surface">
        <AlertCircle className="h-5 w-5 text-danger" />
      </div>
      <h3 className="text-lg font-semibold text-foreground">{title}</h3>
      <p className="text-sm text-muted leading-relaxed">
        {description}
      </p>
    </div>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-card-bg p-6 flex flex-col gap-3 hover:border-accent/30 transition-colors" style={{ boxShadow: "var(--shadow-sm)" }}>
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-surface">
        <Icon className="h-5 w-5 text-accent" />
      </div>
      <h3 className="text-lg font-semibold text-foreground">{title}</h3>
      <p className="text-sm text-muted leading-relaxed">
        {description}
      </p>
    </div>
  );
}

function StepCard({
  number,
  text,
}: {
  number: number;
  text: string;
}) {
  return (
    <div className="flex flex-col items-center gap-4 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent text-white text-lg font-bold" style={{ boxShadow: "var(--shadow-md)" }}>
        {number}
      </div>
      <p className="text-base font-medium text-foreground">{text}</p>
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="mx-auto max-w-6xl px-6 py-24 md:py-32">
          <div className="flex flex-col items-center gap-12 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-1 flex-col gap-6 md:max-w-xl">
              <span className="inline-flex w-fit items-center rounded-full border border-accent/30 bg-accent-surface px-3 py-1.5 text-xs font-medium text-accent-text">
                Inteligência Técnica Operacional
              </span>

              <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
                Seu codebase, explicado em português
              </h1>

              <p className="text-lg text-muted leading-relaxed">
                Assistente técnico interno que aprende o seu sistema e responde
                dúvidas do suporte — sem interromper o dev.
              </p>

              <div className="flex flex-wrap gap-3 pt-2">
                <Link
                  href="/auth/signin"
                  className={cn(
                    "inline-flex items-center gap-2 rounded-xl bg-accent px-6 py-3 text-sm font-semibold text-white",
                    "transition-all hover:bg-accent-dark hover:scale-[1.02]"
                  )}
                >
                  Entrar com GitHub
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="#features"
                  className={cn(
                    "inline-flex items-center gap-2 rounded-xl border border-border px-6 py-3 text-sm font-medium text-foreground",
                    "transition-colors hover:bg-hover"
                  )}
                >
                  Ver como funciona
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </div>
            </div>

            <div className="flex flex-1 justify-center md:justify-end">
              <ChatMockup />
            </div>
          </div>
        </div>
      </section>

      {/* Problem */}
      <section className="border-t border-border bg-hover/50">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-24">
          <h2 className="mb-12 text-center text-3xl font-bold tracking-tight">
            Problemas que você conhece bem
          </h2>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <ProblemCard
              title="Dev interrompido 5–15x por dia"
              description="Suporte não sabe onde ficam as funcionalidades e precisa perguntar ao dev toda hora."
            />
            <ProblemCard
              title="Erros descobertos pelo cliente"
              description="A investigação começa do zero e leva horas até alguém entender o que aconteceu."
            />
            <ProblemCard
              title="Conhecimento que vai embora"
              description="Dev sênior sai da empresa e o conhecimento sobre o sistema vai junto com ele."
            />
          </div>
        </div>
      </section>

      {/* Solution / Features */}
      <section id="features" className="border-t border-border">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-24">
          <h2 className="mb-4 text-center text-3xl font-bold tracking-tight">
            Como o Memora resolve
          </h2>
          <p className="mx-auto mb-12 max-w-2xl text-center text-muted">
            Três camadas de inteligência que trabalham juntas para proteger seu
            time.
          </p>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={MessageSquare}
              title="Assistente de Suporte"
              description="Pergunte em português, receba resposta baseada no seu código real."
            />
            <FeatureCard
              icon={Shield}
              title="Monitor de Erros"
              description="Erros explicados em linguagem simples antes do cliente reclamar."
            />
            <FeatureCard
              icon={Brain}
              title="Memória Técnica"
              description="Decisões e conhecimento do time registrados e pesquisáveis."
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-border bg-hover/50">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-24">
          <h2 className="mb-12 text-center text-3xl font-bold tracking-tight">
            Como funciona
          </h2>

          <div className="grid gap-10 sm:grid-cols-3">
            <StepCard number={1} text="Conecta sua conta GitHub" />
            <StepCard number={2} text="Seleciona os repositórios para indexar" />
            <StepCard number={3} text="Sua equipe começa a perguntar" />
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-24 text-center">
          <h2 className="mb-6 text-3xl font-bold tracking-tight">
            Pronto para eliminar as interrupções?
          </h2>

          <Link
            href="/auth/signin"
            className={cn(
              "inline-flex items-center gap-2 rounded-xl bg-accent px-8 py-3.5 text-base font-semibold text-white",
              "transition-all hover:bg-accent-dark hover:scale-[1.02]"
            )}
          >
            Começar agora — é grátis
            <ArrowRight className="h-4 w-4" />
          </Link>

          <p className="mt-4 text-sm text-muted">
            Sem cartão de crédito. Sem instalação. Funciona em minutos.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-between">
            <div className="flex items-center gap-2">
              <Image src="/logo.png" alt="Memora" width={32} height={32} className="h-8 w-8 rounded-lg" />
              <div className="flex flex-col">
                <span className="text-sm font-semibold text-foreground">
                  Memora
                </span>
                <span className="text-xs text-muted">
                  Inteligência Técnica Operacional
                </span>
              </div>
            </div>

            <div className="flex items-center gap-6 text-sm text-muted">
              <Link href="#" className="transition-colors hover:text-foreground">
                Entrar
              </Link>
              <Link href="#" className="transition-colors hover:text-foreground">
                Política de Privacidade
              </Link>
              <Link href="#" className="transition-colors hover:text-foreground">
                Termos de Uso
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
