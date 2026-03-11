import type { Translations } from "./pt";

export const en: Translations = {
  nav: {
    product: "Product",
    pricing: "Pricing",
    docs: "FAQ",
    cta: "Start free",
  },

  hero: {
    headline: "Turn your codebase\ninto instant answers.",
    subheadline:
      "Connect your repository. In minutes, anyone on the team asks questions about the software and gets answers with code source references. Devs, support and managers.",
    ctaPrimary: "Start 7-day trial",
    ctaSecondary: "See how it works",
  },

  problem: {
    title: "Software knowledge is always fragmented.",
    subtitle:
      "A senior dev interrupted 10x a day loses 2h of deep work. A 6-week onboarding costs $3k+ in salary without delivery. These numbers repeat every month.",
    items: [
      {
        title: "Slow onboarding",
        description: "New developers take 3 to 6 weeks to understand the system. Without updated docs, everyone builds their mental map from scratch.",
      },
      {
        title: "Outdated documentation",
        description: "The docs exist, but nobody trusts them. The code changed 50 times since the last update.",
      },
      {
        title: "Concentrated knowledge",
        description: "Only the original developer understands certain parts of the code. When they leave, the knowledge leaves too.",
      },
      {
        title: "Support depends on devs",
        description: "The support team stops working every time they need a technical answer. The dev is interrupted 5, 10, 15 times a day.",
      },
      {
        title: "Risky changes",
        description: "Nobody knows the real impact of a change. Every deploy is a leap of faith.",
      },
    ],
  },

  solution: {
    title: "Not another chatbot pasted on code. It's a technical intelligence system.",
    description:
      "Common tools throw your code into an LLM and hope the answer makes sense. Memora is different: it decomposes the codebase into semantic units, generates per-function embeddings, and uses hybrid search (vector + text) to find exactly the relevant snippet. The result: answers with real code sources, not hallucinations.",
  },

  howItWorks: {
    title: "How it works",
    subtitle: "From repository to answers in under 10 minutes.",
    steps: [
      {
        number: "01",
        title: "Connect your repository",
        description: "GitHub, GitLab or any Git repository. Secure connection via OAuth in 1 click.",
      },
      {
        number: "02",
        title: "Memora analyzes the codebase",
        description: "The system maps the structure, functions and dependencies of the code using AI. Supports repositories up to 500MB.",
      },
      {
        number: "03",
        title: "Builds the knowledge system",
        description: "Documentation, business rules, dependencies and wikis are generated automatically.",
      },
      {
        number: "04",
        title: "Ask about your software",
        description: "Chat in plain language, with code source references. Answers in under 5 seconds for devs, support and leadership.",
      },
    ],
  },

  benefits: {
    title: "Outcomes that matter",
    items: [
      {
        title: "Onboarding from weeks to days",
        description: "New devs ask Memora instead of interrupting the team. First commit in days, not 6 weeks.",
      },
      {
        title: "Always up-to-date documentation",
        description: "AI-generated, aligned with the actual code. No more outdated docs.",
      },
      {
        title: "Incidents resolved in half the time",
        description: "AI hypotheses, automatic timeline and post-mortem generated instantly.",
      },
      {
        title: "Support that doesn't interrupt devs",
        description: "Support team finds answers on their own. Fewer interruptions, more productivity.",
      },
      {
        title: "Clear impact before every change",
        description: "Know what can break before changing a single line of code.",
      },
      {
        title: "Executive visibility in 1 dashboard",
        description: "Consolidated technical health metrics for CTOs and tech leads.",
      },
    ],
  },

  useCases: {
    title: "Who is Memora for",
    items: [
      {
        title: "Engineering teams",
        description: "Living documentation, automated code review and impact analysis before every PR.",
      },
      {
        title: "Technical support",
        description: "Instant answers about the system without depending on devs. Faster resolution.",
      },
      {
        title: "CTOs and tech leads",
        description: "Real visibility into code health, technical risks and architecture decisions.",
      },
      {
        title: "Incident response",
        description: "AI-powered war room, automatic hypotheses and similar incident history.",
      },
      {
        title: "Product teams",
        description: "Understand business rules and dependencies before planning the next feature.",
      },
    ],
  },

  modules: {
    title: "7 integrated modules",
    subtitle: "Everything your technical operation needs in one platform.",
    items: [
      {
        title: "Assistant",
        description: "Smart chat that answers code questions with sources and context.",
      },
      {
        title: "Technical Memory",
        description: "Automatically captures knowledge from PRs, commits, issues and documents.",
      },
      {
        title: "Documentation",
        description: "Generates and maintains updated docs from code. No more obsolete docs.",
      },
      {
        title: "Impact Analysis",
        description: "Maps dependencies and assesses risk before any code change.",
      },
      {
        title: "Incident Management",
        description: "War room, timeline, AI hypotheses and automatically generated post-mortem.",
      },
      {
        title: "Error Monitor",
        description: "Receives logs in real-time, analyzes with AI and generates alerts with suggested actions.",
      },
      {
        title: "Executive Dashboard",
        description: "Weekly metrics for security, errors, support and code quality.",
      },
    ],
  },

  pricing: {
    title: "Simple pricing, real value",
    subtitle: "Start with 7 free days. No credit card required.",
    plans: {
      pro: {
        name: "Pro",
        badge: "Most popular",
        price: "$97",
        period: "/mo",
        description: "All modules. Multi-repo. Unlimited users.",
        features: [
          "All 7 modules included",
          "Up to 50 repositories",
          "Unlimited users",
          "Email support",
          "7-day free trial",
        ],
        cta: "Start 7-day trial",
        roi: "Senior dev costs ~$75/hr. Save 1h/day = $1,650/mo. The plan pays for itself 17x.",
      },
      enterprise: {
        name: "Enterprise",
        badge: "Self-hosted",
        price: "$297",
        period: "/mo",
        description: "Database on your infrastructure. Full compliance and GDPR.",
        features: [
          "Everything in Pro",
          "Self-hosted database",
          "Dedicated SLA",
          "Priority support",
          "GDPR on-premise",
          "Assisted setup",
        ],
        cta: "Talk to sales",
      },
    },
  },

  faq: {
    title: "Frequently asked questions",
    items: [
      {
        q: "What is the 7-day trial?",
        a: "Full access to all Pro plan modules for 7 days, no credit card required. If you like it, just subscribe. If not, your data is automatically removed.",
      },
      {
        q: "Where is my code stored?",
        a: "On Pro, in Supabase (managed PostgreSQL) with encryption at rest. On Enterprise, 100% on your infrastructure. Data never leaves your environment.",
      },
      {
        q: "Does it work with any language?",
        a: "Yes. Indexes any Git repository. Analysis optimized for Python, but works with JavaScript, TypeScript, Java, Go, Ruby and others.",
      },
      {
        q: "Do I need technical knowledge to set up?",
        a: "No. Guided onboarding in under 10 minutes: create account, configure AI, connect GitHub and index your first repository. All via web interface.",
      },
      {
        q: "Can I cancel anytime?",
        a: "Yes. No lock-in, no penalty. Cancel at any time and your data is removed within 30 days.",
      },
      {
        q: "Which AIs does Memora support?",
        a: "OpenAI (GPT-4o), Anthropic (Claude), Google (Gemini), Groq and Ollama (local models). You choose the provider and model per organization.",
      },
    ],
  },

  finalCta: {
    headline: "Every week without Memora is knowledge walking out the door.",
    subheadline: "Setup in 10 minutes. 7 free days with full access. No credit card.",
    ctaPrimary: "Start 7-day trial",
    ctaSecondary: "Create workspace now",
  },

  footer: {
    tagline: "Operational technical intelligence for software companies.",
    rights: "© 2026 Memora by Orbitalis. All rights reserved.",
    product: "Product",
    pricing: "Pricing",
  },
} as const;
