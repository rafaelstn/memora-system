import Image from "next/image";
import Link from "next/link";
import {
  AlertCircle,
  MessageSquare,
  Shield,
  Brain,
  ArrowRight,
  ChevronRight,
  Eye,
  FileSearch,
  Code2,
  BookOpen,
  Zap,
  Clock,
  Users,
  TrendingDown,
  DollarSign,
  Building2,
  Rocket,
  Target,
  CheckCircle2,
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
            Onde fica a logica de calculo de frete?
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Image src="/logo.png" alt="Memora" width={32} height={32} className="h-8 w-8 shrink-0 rounded-full" />
          <div className="flex flex-col gap-2 rounded-xl bg-hover px-4 py-2.5 text-sm text-foreground">
            <p>
              A logica de frete esta em{" "}
              <code className="rounded-md bg-accent-surface px-1.5 py-0.5 text-xs font-mono text-accent-text">
                src/services/shipping.ts
              </code>
            </p>
            <p>
              Ela calcula o valor com base na zona de entrega e peso do pacote.
              Foi alterada pela ultima vez em 12/fev por @carlos para incluir
              a tabela de zonas atualizada.
            </p>
            <p className="text-muted text-xs">
              Fonte: codigo + historico de alteracoes
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

function ModuleCard({
  icon: Icon,
  title,
  description,
  metric,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  metric: string;
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
      <p className="text-sm font-semibold text-accent mt-auto pt-2">
        {metric}
      </p>
    </div>
  );
}

function StepCard({
  number,
  title,
  description,
}: {
  number: number;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center gap-4 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-white text-xl font-bold" style={{ boxShadow: "var(--shadow-md)" }}>
        {number}
      </div>
      <h3 className="text-lg font-semibold text-foreground">{title}</h3>
      <p className="text-sm text-muted leading-relaxed max-w-xs">
        {description}
      </p>
    </div>
  );
}

function ROICard({
  icon: Icon,
  value,
  label,
}: {
  icon: React.ElementType;
  value: string;
  label: string;
}) {
  return (
    <div className="flex flex-col items-center gap-3 text-center p-6">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent-surface">
        <Icon className="h-6 w-6 text-accent" />
      </div>
      <span className="text-3xl font-bold text-foreground">{value}</span>
      <span className="text-sm text-muted">{label}</span>
    </div>
  );
}

function AudienceCard({
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

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="mx-auto max-w-6xl px-6 py-24 md:py-32">
          <div className="flex flex-col items-center gap-12 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-1 flex-col gap-6 md:max-w-xl">
              <span className="inline-flex w-fit items-center rounded-full border border-accent/30 bg-accent-surface px-3 py-1.5 text-xs font-medium text-accent-text">
                Inteligencia Tecnica Operacional
              </span>

              <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
                O sistema que se explica sozinho.
              </h1>

              <div className="flex flex-col gap-3 text-lg text-muted leading-relaxed">
                <p>Seu time de suporte responde sem acionar o dev.</p>
                <p>Seus erros sao detectados antes do cliente reclamar.</p>
                <p>Seu conhecimento tecnico nunca mais vai embora com um dev.</p>
              </div>

              <div className="flex flex-wrap gap-3 pt-2">
                <Link
                  href="/auth/signin"
                  className={cn(
                    "inline-flex items-center gap-2 rounded-xl bg-accent px-6 py-3 text-sm font-semibold text-white",
                    "transition-all hover:bg-accent-dark hover:scale-[1.02]"
                  )}
                >
                  Quero conhecer o Memora
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="#solucao"
                  className={cn(
                    "inline-flex items-center gap-2 rounded-xl border border-border px-6 py-3 text-sm font-medium text-foreground",
                    "transition-colors hover:bg-hover"
                  )}
                >
                  Ver o que resolve
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
          <h2 className="mb-4 text-center text-3xl font-bold tracking-tight">
            Problemas que voce conhece bem
          </h2>
          <p className="mx-auto mb-12 max-w-2xl text-center text-muted">
            Se sua empresa desenvolve software, pelo menos tres desses problemas
            estao custando dinheiro agora.
          </p>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <ProblemCard
              title="Dev interrompido 5-15x por dia"
              description="Suporte nao sabe onde ficam as funcionalidades e precisa perguntar ao dev toda hora."
            />
            <ProblemCard
              title="Erros descobertos pelo cliente"
              description="A investigacao comeca do zero e leva horas ate alguem entender o que aconteceu."
            />
            <ProblemCard
              title="Conhecimento que vai embora"
              description="Dev senior sai da empresa e o conhecimento sobre o sistema vai junto com ele."
            />
            <ProblemCard
              title="PRs sem revisao de verdade"
              description="Codigo entra em producao sem ninguem olhar seguranca, performance ou padroes do time."
            />
            <ProblemCard
              title="Incidentes sem historico"
              description="Quando um problema grave acontece, ninguem sabe o que ja foi tentado antes ou como foi resolvido."
            />
            <ProblemCard
              title="Documentacao desatualizada ou inexistente"
              description="Ninguem tem tempo de documentar, e quando documenta, fica desatualizado em uma semana."
            />
          </div>
        </div>
      </section>

      {/* Solution / Modules */}
      <section id="solucao" className="border-t border-border">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-24">
          <h2 className="mb-4 text-center text-3xl font-bold tracking-tight">
            O que o Memora faz pela sua empresa
          </h2>
          <p className="mx-auto mb-12 max-w-2xl text-center text-muted">
            Sete modulos que trabalham juntos para proteger o conhecimento,
            acelerar o suporte e prevenir problemas.
          </p>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <ModuleCard
              icon={MessageSquare}
              title="Assistente de Suporte"
              description="O suporte responde duvidas sobre o sistema em segundos, sem precisar acionar o dev."
              metric="Reduz interrupcoes ao dev em ate 80%"
            />
            <ModuleCard
              icon={Shield}
              title="Monitor de Erros"
              description="Erros sao detectados, explicados e notificados automaticamente — antes do cliente perceber."
              metric="Tempo de deteccao reduzido de horas para minutos"
            />
            <ModuleCard
              icon={Brain}
              title="Memoria Tecnica"
              description="Todo conhecimento do time — decisoes, mudancas, motivos — fica registrado e pesquisavel para sempre."
              metric="Zero perda de conhecimento em turnover"
            />
            <ModuleCard
              icon={Eye}
              title="Revisao de Codigo"
              description="Cada PR e revisado automaticamente em seguranca, performance, bugs e padroes do time."
              metric="Problemas encontrados antes de chegar em producao"
            />
            <ModuleCard
              icon={Zap}
              title="Gestao de Incidentes"
              description="Quando algo grave acontece, o Memora organiza a investigacao, sugere hipoteses e gera o postmortem."
              metric="Tempo medio de resolucao reduzido em 40%"
            />
            <ModuleCard
              icon={BookOpen}
              title="Documentacao Automatica"
              description="Documentacao gerada e atualizada automaticamente a partir do proprio sistema. Sempre atual."
              metric="Documentacao que se mantem sozinha"
            />
            <ModuleCard
              icon={Code2}
              title="Geracao de Codigo"
              description="Gera codigo consistente com os padroes do seu projeto, acelerando entregas sem perder qualidade."
              metric="Entregas ate 3x mais rapidas em tarefas repetitivas"
            />
          </div>
        </div>
      </section>

      {/* ROI */}
      <section className="border-t border-border bg-hover/50">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-24">
          <h2 className="mb-4 text-center text-3xl font-bold tracking-tight">
            O retorno e mensuravel
          </h2>
          <p className="mx-auto mb-12 max-w-2xl text-center text-muted">
            Numeros reais de times que pararam de perder tempo com problemas evitaveis.
          </p>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <ROICard
              icon={Clock}
              value="80%"
              label="menos interrupcoes ao dev"
            />
            <ROICard
              icon={TrendingDown}
              value="60%"
              label="reducao no tempo de investigacao de erros"
            />
            <ROICard
              icon={Users}
              value="0"
              label="conhecimento perdido em turnover"
            />
            <ROICard
              icon={DollarSign}
              value="5-15h"
              label="economizadas por dev por semana"
            />
          </div>
        </div>
      </section>

      {/* Para quem e */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-24">
          <h2 className="mb-4 text-center text-3xl font-bold tracking-tight">
            Para quem e o Memora
          </h2>
          <p className="mx-auto mb-12 max-w-2xl text-center text-muted">
            Feito para empresas brasileiras que desenvolvem software e precisam
            escalar sem perder controle.
          </p>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <AudienceCard
              icon={Building2}
              title="Software houses e agencias"
              description="Times de 5 a 50 devs que precisam manter multiplos projetos sem perder qualidade."
            />
            <AudienceCard
              icon={Rocket}
              title="Startups em crescimento"
              description="Empresas que estao escalando rapido e nao podem depender de uma unica pessoa que sabe tudo."
            />
            <AudienceCard
              icon={Target}
              title="PMEs com time de tecnologia"
              description="Empresas com sistema proprio que precisam de suporte eficiente e menos dependencia do dev."
            />
          </div>
        </div>
      </section>

      {/* Como o Memora entra na sua empresa */}
      <section className="border-t border-border bg-hover/50">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-24">
          <h2 className="mb-12 text-center text-3xl font-bold tracking-tight">
            Como o Memora entra na sua empresa
          </h2>

          <div className="grid gap-10 sm:grid-cols-3">
            <StepCard
              number={1}
              title="Implementacao"
              description="Em ate 1 semana o Memora esta configurado e integrado ao seu ambiente. Sem mudar nada no seu time ou processo atual."
            />
            <StepCard
              number={2}
              title="Aprendizado"
              description="O Memora aprende o seu sistema automaticamente. Quanto mais usado, mais preciso fica. Nenhum esforco manual de documentacao necessario."
            />
            <StepCard
              number={3}
              title="Resultado"
              description="Em 30 dias voce tem metricas reais: menos interrupcoes, erros detectados antes, time mais produtivo."
            />
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-24 text-center">
          <h2 className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl">
            Seu time merece trabalhar no que importa.
          </h2>
          <p className="mx-auto mb-8 max-w-xl text-lg text-muted">
            Pare de perder horas com interrupcoes, erros evitaveis e conhecimento
            que vai embora. Converse com a gente.
          </p>

          <div className="flex flex-col items-center gap-4">
            <Link
              href="/auth/signin"
              className={cn(
                "inline-flex items-center gap-2 rounded-xl bg-accent px-8 py-3.5 text-base font-semibold text-white",
                "transition-all hover:bg-accent-dark hover:scale-[1.02]"
              )}
            >
              Falar com a equipe Memora
              <ArrowRight className="h-4 w-4" />
            </Link>

            <p className="text-sm text-muted">
              Sem compromisso. Sem cartao de credito. Implementacao em ate 1 semana.
            </p>
          </div>
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
                  Inteligencia Tecnica Operacional
                </span>
              </div>
            </div>

            <div className="flex items-center gap-6 text-sm text-muted">
              <Link href="/auth/signin" className="transition-colors hover:text-foreground">
                Entrar
              </Link>
              <Link href="#" className="transition-colors hover:text-foreground">
                Politica de Privacidade
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
