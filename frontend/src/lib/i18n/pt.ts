export const pt = {
  nav: {
    product: "Produto",
    pricing: "Preços",
    docs: "FAQ",
    cta: "Começar grátis",
  },

  hero: {
    headline: "Transforme seu codebase\nem respostas instantâneas.",
    subheadline:
      "Conecte seu repositório. Em minutos, qualquer pessoa do time pergunta sobre o software e recebe respostas com fontes no código. Devs, suporte e gestores.",
    ctaPrimary: "Começar trial de 7 dias",
    ctaSecondary: "Ver como funciona",
  },

  problem: {
    title: "O conhecimento do software está sempre fragmentado.",
    subtitle:
      "Um dev sênior interrompido 10x ao dia perde 2h de trabalho profundo. Um onboarding de 6 semanas custa R$15k+ em salário sem entrega. Esses números se repetem todo mês.",
    items: [
      {
        title: "Onboarding lento",
        description: "Devs novos levam 3 a 6 semanas para entender o sistema. Sem documentação atualizada, cada um monta seu mapa mental do zero.",
      },
      {
        title: "Documentação desatualizada",
        description: "A doc existe, mas ninguém confia. O código mudou 50 vezes desde a última atualização.",
      },
      {
        title: "Conhecimento concentrado",
        description: "Só o dev original entende certas partes do código. Quando ele sai, o conhecimento vai junto.",
      },
      {
        title: "Suporte depende do dev",
        description: "O time de suporte para o trabalho toda vez que precisa de uma resposta técnica. O dev é interrompido 5, 10, 15 vezes por dia.",
      },
      {
        title: "Mudanças arriscadas",
        description: "Ninguém sabe o impacto real de uma alteração. Cada deploy é um exercício de fé.",
      },
    ],
  },

  solution: {
    title: "Não é mais um chatbot colado no código. É um sistema de inteligência técnica.",
    description:
      "Ferramentas comuns jogam seu código num LLM e torcem para a resposta fazer sentido. O Memora é diferente: ele decompõe o codebase em unidades semânticas, gera embeddings por função, e usa busca híbrida (vetorial + textual) para encontrar exatamente o trecho relevante. O resultado: respostas com fontes reais no código, não alucinações.",
  },

  howItWorks: {
    title: "Como funciona",
    subtitle: "Do repositório às respostas em menos de 10 minutos.",
    steps: [
      {
        number: "01",
        title: "Conecte seu repositório",
        description: "GitHub, GitLab ou qualquer repositório Git. Conexão segura via OAuth em 1 clique.",
      },
      {
        number: "02",
        title: "Memora analisa o codebase",
        description: "O sistema mapeia a estrutura, funções e dependências do código usando IA. Suporta repositórios de até 500MB.",
      },
      {
        number: "03",
        title: "Constrói o sistema de conhecimento",
        description: "Documentação, regras de negócio, dependências e wikis são gerados automaticamente.",
      },
      {
        number: "04",
        title: "Pergunte sobre o software",
        description: "Chat em português, com fontes no código. Respostas em menos de 5 segundos para devs, suporte e liderança.",
      },
    ],
  },

  benefits: {
    title: "Resultados que importam",
    items: [
      {
        title: "Onboarding de semanas para dias",
        description: "Dev novo pergunta ao Memora em vez de interromper o time. Primeiro commit em dias, não em 6 semanas.",
      },
      {
        title: "Documentação sempre atualizada",
        description: "Gerada por IA, alinhada com o código real. Nunca mais doc desatualizada.",
      },
      {
        title: "Incidentes resolvidos em metade do tempo",
        description: "Hipóteses de IA, timeline automática e post-mortem gerado instantaneamente.",
      },
      {
        title: "Suporte que não interrompe o dev",
        description: "O time de suporte encontra respostas sozinho. Menos interrupções, mais produtividade.",
      },
      {
        title: "Impacto claro antes de cada mudança",
        description: "Saiba o que pode quebrar antes de alterar uma linha de código.",
      },
      {
        title: "Visibilidade executiva em 1 dashboard",
        description: "Métricas consolidadas de saúde técnica para CTOs e tech leads.",
      },
    ],
  },

  useCases: {
    title: "Para quem é o Memora",
    items: [
      {
        title: "Times de engenharia",
        description: "Documentação viva, code review automatizado e análise de impacto antes de cada PR.",
      },
      {
        title: "Suporte técnico",
        description: "Respostas instantâneas sobre o sistema sem depender do dev. Resolução mais rápida.",
      },
      {
        title: "CTOs e tech leads",
        description: "Visibilidade real sobre saúde do código, riscos técnicos e decisões de arquitetura.",
      },
      {
        title: "Resposta a incidentes",
        description: "War room com IA, hipóteses automáticas e histórico de incidentes similares.",
      },
      {
        title: "Times de produto",
        description: "Entenda regras de negócio e dependências antes de planejar a próxima feature.",
      },
    ],
  },

  modules: {
    title: "7 módulos integrados",
    subtitle: "Tudo que sua operação técnica precisa em uma plataforma.",
    items: [
      {
        title: "Assistente",
        description: "Chat inteligente que responde perguntas sobre o código com fontes e contexto.",
      },
      {
        title: "Memória Técnica",
        description: "Captura conhecimento de PRs, commits, issues e documentos automaticamente.",
      },
      {
        title: "Documentação",
        description: "Gera e mantém docs atualizadas a partir do código. Nunca mais doc obsoleta.",
      },
      {
        title: "Análise de Impacto",
        description: "Mapeia dependências e avalia o risco antes de qualquer alteração no código.",
      },
      {
        title: "Gestão de Incidentes",
        description: "War room, timeline, hipóteses de IA e post-mortem gerado automaticamente.",
      },
      {
        title: "Monitor de Erros",
        description: "Recebe logs em tempo real, analisa com IA e gera alertas com ações sugeridas.",
      },
      {
        title: "Painel Executivo",
        description: "Métricas semanais de segurança, erros, suporte e qualidade de código.",
      },
    ],
  },

  pricing: {
    title: "Preços simples, valor real",
    subtitle: "Comece com 7 dias grátis. Sem cartão de crédito.",
    plans: {
      pro: {
        name: "Pro",
        badge: "Mais popular",
        price: "R$497",
        period: "/mês",
        description: "Todos os módulos. Multi-repositório. Usuários ilimitados.",
        features: [
          "Todos os 7 módulos inclusos",
          "Até 50 repositórios",
          "Usuários ilimitados",
          "Suporte por email",
          "7 dias de trial grátis",
        ],
        cta: "Começar trial de 7 dias",
        roi: "Dev sênior custa ~R$150/hora. Economize 1h/dia = R$3.300/mês. O plano se paga 6x.",
      },
      enterprise: {
        name: "Enterprise",
        badge: "Infra própria",
        price: "R$1.497",
        period: "/mês",
        description: "Banco de dados na sua infraestrutura. Compliance e LGPD total.",
        features: [
          "Tudo do Pro",
          "Banco de dados próprio",
          "SLA dedicado",
          "Suporte prioritário",
          "LGPD on-premise",
          "Setup assistido",
        ],
        cta: "Falar com a equipe",
      },
    },
  },

  faq: {
    title: "Perguntas frequentes",
    items: [
      {
        q: "O que é o trial de 7 dias?",
        a: "Acesso completo a todos os módulos do plano Pro durante 7 dias, sem cartão de crédito. Se gostar, é só assinar. Se não, seus dados são removidos automaticamente.",
      },
      {
        q: "Meu código fica armazenado onde?",
        a: "No Pro, no Supabase (PostgreSQL gerenciado) com criptografia em repouso. No Enterprise, 100% na sua infraestrutura. Os dados nunca saem do seu ambiente.",
      },
      {
        q: "Funciona com qualquer linguagem?",
        a: "Sim. Indexa qualquer repositório Git. Análise otimizada para Python, mas funciona com JavaScript, TypeScript, Java, Go, Ruby e outras.",
      },
      {
        q: "Preciso de conhecimento técnico para configurar?",
        a: "Não. Onboarding guiado em menos de 10 minutos: criar conta, configurar IA, conectar GitHub e indexar o primeiro repositório. Tudo via interface web.",
      },
      {
        q: "Posso cancelar quando quiser?",
        a: "Sim. Sem fidelidade, sem multa. Cancele a qualquer momento e seus dados são removidos em até 30 dias.",
      },
      {
        q: "Quais IAs o Memora suporta?",
        a: "OpenAI (GPT-4o), Anthropic (Claude), Google (Gemini), Groq e Ollama (modelos locais). Você escolhe o provider e modelo por organização.",
      },
    ],
  },

  finalCta: {
    headline: "Cada semana sem Memora é conhecimento que sai pela porta com alguém.",
    subheadline: "Setup em 10 minutos. 7 dias grátis com acesso total. Sem cartão de crédito.",
    ctaPrimary: "Começar trial de 7 dias",
    ctaSecondary: "Criar workspace agora",
  },

  footer: {
    tagline: "Inteligência técnica operacional para empresas de software.",
    rights: "© 2026 Memora by Orbitalis. Todos os direitos reservados.",
    product: "Produto",
    pricing: "Preços",
  },
};

export type Translations = typeof pt;
