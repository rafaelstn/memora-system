export const pt = {
  // Nav
  nav: {
    product: "Produto",
    pricing: "Preços",
    enterprise: "Enterprise",
    customer: "Customer",
    cta: "Começar grátis",
  },

  // Hero
  hero: {
    badge: "Novo — Geração de Código com MCP agora disponível",
    headline: "O sistema que se explica sozinho.",
    subheadline:
      "Memora transforma o codebase da sua empresa em inteligência acessível — para o suporte, para os devs e para o negócio.",
    ctaPrimary: "Começar trial de 7 dias",
    ctaSecondary: "Ver como funciona",
    metric1: "↓ 73% menos interrupções ao dev",
    metric2: "⚡ Erros detectados em < 5 min",
    metric3: "📚 Onboarding em dias, não semanas",
  },

  // Pain points
  pains: {
    title: "Você reconhece algum desses cenários?",
    items: [
      {
        title: "O suporte para tudo para perguntar ao dev",
        description: "Cada dúvida técnica vira uma interrupção no time de desenvolvimento.",
        solution: "Assistente de Suporte",
      },
      {
        title: "Erros em produção são descobertos pelo cliente",
        description: "Sem monitoramento inteligente, o cliente avisa antes do time.",
        solution: "Monitor de Erros",
      },
      {
        title: "Dev sênior sai e o conhecimento vai junto",
        description: "Decisões técnicas não documentadas se perdem com a rotatividade.",
        solution: "Memória Técnica",
      },
      {
        title: "Código de IA vai direto pra produção sem revisão",
        description: "Copilot e ChatGPT geram código que ninguém revisa antes do merge.",
        solution: "Revisão de Código IA",
      },
      {
        title: "Dev novo leva semanas pra ser produtivo",
        description: "Sem documentação atualizada, o onboarding é lento e frustrante.",
        solution: "Documentação + Onboarding",
      },
      {
        title: "Ninguém sabe ao certo o que o sistema faz",
        description: "Regras de negócio estão espalhadas no código sem mapeamento.",
        solution: "Regras de Negócio",
      },
    ],
  },

  // Demo
  demo: {
    title: "Veja o Memora em ação",
    subtitle: "11 módulos integrados para inteligência técnica completa",
    modules: [
      {
        id: "assistant",
        label: "Assistente",
        title: "Assistente de Suporte",
        description:
          "Pergunte qualquer coisa sobre o código em português. O assistente busca no codebase indexado e responde com fontes.",
      },
      {
        id: "monitor",
        label: "Monitor",
        title: "Monitor de Erros",
        description:
          "Recebe logs em tempo real, analisa com IA e gera alertas com explicação em português, severidade e ações sugeridas.",
      },
      {
        id: "memory",
        label: "Memória",
        title: "Memória Técnica",
        description:
          "Captura conhecimento de PRs, commits, issues e documentos. Gera wikis por componente automaticamente.",
      },
      {
        id: "review",
        label: "Revisão",
        title: "Revisão de Código IA",
        description:
          "5 análises paralelas (bugs, segurança, performance, consistência, padrões) com score e comentários no PR.",
      },
      {
        id: "docs",
        label: "Documentação",
        title: "Documentação Automática",
        description:
          "Gera e mantém documentação atualizada a partir do código. Processa PDFs, DOCXs e markdowns existentes.",
      },
      {
        id: "rules",
        label: "Regras",
        title: "Regras de Negócio",
        description:
          "Mapeia e extrai regras de negócio do código em linguagem natural. Identifica complexidade e dependências.",
      },
      {
        id: "codegen",
        label: "Geração",
        title: "Geração de Código",
        description:
          "Gera código consistente com os padrões do projeto via MCP. Entende o contexto completo do codebase.",
      },
      {
        id: "impact",
        label: "Impacto",
        title: "Análise de Impacto",
        description:
          "Antes de mudar, saiba o que pode quebrar. Mapeia dependências e avalia risco de alterações.",
      },
      {
        id: "incidents",
        label: "Incidentes",
        title: "Gestão de Incidentes",
        description:
          "War room com timeline, hipóteses de IA, incidentes similares e post-mortem gerado automaticamente.",
      },
      {
        id: "executive",
        label: "Executivo",
        title: "Painel Executivo",
        description:
          "Métricas semanais consolidadas: segurança, erros, suporte, reviews, incidentes. Trend analysis e CSV export.",
      },
      {
        id: "security",
        label: "Segurança",
        title: "Análise de Segurança",
        description:
          "Scan estático e DAST com prevenção de SSRF. Audit log, rate limiting e refresh tokens.",
      },
    ],
  },

  // Pricing
  pricing: {
    title: "Preços simples, valor real",
    subtitle: "Comece com 7 dias grátis. Sem cartão de crédito.",
    earlyAdopter: "Primeiros 3 clientes: R$397/mês — preço travado para sempre",
    plans: {
      pro: {
        name: "PRO",
        badge: "Mais popular",
        price: "R$497",
        period: "/mês",
        description:
          "Infraestrutura Memora completa. Todos os módulos, multi-repositório, multi-usuário.",
        features: [
          "Todos os 11 módulos inclusos",
          "Até 50 repositórios",
          "Usuários ilimitados",
          "Suporte por email",
          "Atualizações automáticas",
          "7 dias de trial grátis",
        ],
        cta: "Começar trial de 7 dias",
        note: "Sem cartão de crédito no trial",
        roi: "1 hora de dev sênior economizada por dia já paga o plano",
      },
      enterprise: {
        name: "Enterprise",
        badge: "Segurança máxima",
        price: "R$1.497",
        period: "/mês",
        description:
          "Banco de dados na sua infraestrutura. Compliance total, dados nunca saem do seu ambiente.",
        features: [
          "Tudo do PRO",
          "Banco de dados próprio",
          "SSO (em breve)",
          "SLA dedicado",
          "Suporte prioritário",
          "LGPD on-premise",
          "Setup assistido",
        ],
        cta: "Falar com a equipe",
      },
      customer: {
        name: "Customer",
        badge: "Sob medida",
        price: "Entre em contato",
        period: "",
        description:
          "Implementação personalizada da inteligência técnica na operação da sua empresa.",
        features: [
          "Consultoria de implementação",
          "Módulos personalizados",
          "Integração com sistemas existentes",
          "Treinamento do time",
          "Suporte dedicado",
          "SLA customizado",
        ],
        cta: "Falar com a equipe",
      },
    },
  },

  // FAQ
  faq: {
    title: "Perguntas frequentes",
    items: [
      {
        q: "O que é o trial de 7 dias?",
        a: "Você tem acesso completo a todos os módulos do plano PRO durante 7 dias, sem precisar cadastrar cartão de crédito. Se gostar, é só assinar. Se não, seus dados são removidos automaticamente.",
      },
      {
        q: "Meu código fica armazenado onde?",
        a: "No plano PRO, o código é indexado e armazenado de forma segura no Supabase (PostgreSQL gerenciado com criptografia em repouso). No Enterprise, os dados ficam 100% na sua infraestrutura.",
      },
      {
        q: "Qual a diferença entre PRO e Enterprise?",
        a: "O PRO usa a infraestrutura gerenciada do Memora. O Enterprise conecta ao banco de dados da sua empresa — os dados operacionais nunca saem do seu ambiente. Ideal para compliance e LGPD.",
      },
      {
        q: "Preciso de conhecimento técnico para instalar?",
        a: "Não. O onboarding guiado leva menos de 10 minutos: criar conta, configurar o LLM provider, conectar o GitHub e indexar o primeiro repositório. Tudo via interface web.",
      },
      {
        q: "Funciona com qualquer linguagem de programação?",
        a: "Sim. O Memora indexa qualquer repositório Git. A análise AST é otimizada para Python, mas o sistema funciona com JavaScript, TypeScript, Java, Go, Ruby e outras linguagens.",
      },
      {
        q: "O que é o plano Customer?",
        a: "É uma implementação personalizada onde a Orbitalis adapta o Memora à operação da sua empresa: módulos customizados, integração com sistemas existentes, treinamento e suporte dedicado.",
      },
      {
        q: "Posso cancelar quando quiser?",
        a: "Sim. Não há fidelidade. Você pode cancelar a qualquer momento e seus dados serão removidos em até 30 dias (ou imediatamente, se preferir).",
      },
      {
        q: "Quais LLMs o Memora suporta?",
        a: "OpenAI (GPT-4o, GPT-4-turbo), Anthropic (Claude), Google (Gemini), Groq (Llama, Mixtral) e Ollama (modelos locais). Você escolhe o provider e modelo por organização.",
      },
    ],
  },

  // Final CTA
  cta: {
    headline: "Seu sistema está pronto para se explicar sozinho.",
    subheadline: "Comece agora. Os primeiros 7 dias são por nossa conta.",
    button: "Começar trial grátis",
  },

  // Footer
  footer: {
    tagline: "Inteligência Técnica Operacional",
    rights: "© 2026 Memora. Todos os direitos reservados.",
    product: "Produto",
    pricing: "Preços",
    enterprise: "Enterprise",
    customer: "Customer",
  },
};

export type Translations = {
  nav: { product: string; pricing: string; enterprise: string; customer: string; cta: string };
  hero: { badge: string; headline: string; subheadline: string; ctaPrimary: string; ctaSecondary: string; metric1: string; metric2: string; metric3: string };
  pains: { title: string; items: { title: string; description: string; solution: string }[] };
  demo: { title: string; subtitle: string; modules: { id: string; label: string; title: string; description: string }[] };
  pricing: {
    title: string; subtitle: string; earlyAdopter: string;
    plans: {
      pro: { name: string; badge: string; price: string; period: string; description: string; features: string[]; cta: string; note: string; roi: string };
      enterprise: { name: string; badge: string; price: string; period: string; description: string; features: string[]; cta: string };
      customer: { name: string; badge: string; price: string; period: string; description: string; features: string[]; cta: string };
    };
  };
  faq: { title: string; items: { q: string; a: string }[] };
  cta: { headline: string; subheadline: string; button: string };
  footer: { tagline: string; rights: string; product: string; pricing: string; enterprise: string; customer: string };
};
