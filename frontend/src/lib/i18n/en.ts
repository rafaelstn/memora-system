import type { Translations } from "./pt";

export const en: Translations = {
  // Nav
  nav: {
    product: "Product",
    pricing: "Pricing",
    enterprise: "Enterprise",
    customer: "Customer",
    cta: "Start free",
  },

  // Hero
  hero: {
    badge: "New — Code Generation with MCP now available",
    headline: "The system that explains itself.",
    subheadline:
      "Memora turns your company's codebase into accessible intelligence — for support, for devs, and for the business.",
    ctaPrimary: "Start 7-day trial",
    ctaSecondary: "See how it works",
    metric1: "↓ 73% fewer dev interruptions",
    metric2: "⚡ Errors detected in < 5 min",
    metric3: "📚 Onboarding in days, not weeks",
  },

  // Pain points
  pains: {
    title: "Do you recognize any of these scenarios?",
    items: [
      {
        title: "Support stops everything to ask the dev",
        description: "Every technical question becomes a dev team interruption.",
        solution: "Support Assistant",
      },
      {
        title: "Production errors are discovered by the customer",
        description: "Without smart monitoring, the customer reports before the team.",
        solution: "Error Monitor",
      },
      {
        title: "Senior dev leaves and the knowledge goes with them",
        description: "Undocumented technical decisions are lost with turnover.",
        solution: "Technical Memory",
      },
      {
        title: "AI code goes straight to production without review",
        description: "Copilot and ChatGPT generate code nobody reviews before merging.",
        solution: "AI Code Review",
      },
      {
        title: "New dev takes weeks to become productive",
        description: "Without updated docs, onboarding is slow and frustrating.",
        solution: "Documentation + Onboarding",
      },
      {
        title: "Nobody knows exactly what the system does",
        description: "Business rules are scattered across the code without mapping.",
        solution: "Business Rules",
      },
    ],
  },

  // Demo
  demo: {
    title: "See Memora in action",
    subtitle: "11 integrated modules for complete technical intelligence",
    modules: [
      {
        id: "assistant",
        label: "Assistant",
        title: "Support Assistant",
        description:
          "Ask anything about the code in plain language. The assistant searches the indexed codebase and responds with sources.",
      },
      {
        id: "monitor",
        label: "Monitor",
        title: "Error Monitor",
        description:
          "Receives logs in real-time, analyzes with AI, and generates alerts with explanations, severity, and suggested actions.",
      },
      {
        id: "memory",
        label: "Memory",
        title: "Technical Memory",
        description:
          "Captures knowledge from PRs, commits, issues, and documents. Generates per-component wikis automatically.",
      },
      {
        id: "review",
        label: "Review",
        title: "AI Code Review",
        description:
          "5 parallel analyses (bugs, security, performance, consistency, patterns) with score and PR comments.",
      },
      {
        id: "docs",
        label: "Docs",
        title: "Auto Documentation",
        description:
          "Generates and maintains updated documentation from code. Processes existing PDFs, DOCXs, and markdowns.",
      },
      {
        id: "rules",
        label: "Rules",
        title: "Business Rules",
        description:
          "Maps and extracts business rules from code in natural language. Identifies complexity and dependencies.",
      },
      {
        id: "codegen",
        label: "CodeGen",
        title: "Code Generation",
        description:
          "Generates code consistent with project patterns via MCP. Understands the full codebase context.",
      },
      {
        id: "impact",
        label: "Impact",
        title: "Impact Analysis",
        description:
          "Before changing, know what can break. Maps dependencies and assesses change risk.",
      },
      {
        id: "incidents",
        label: "Incidents",
        title: "Incident Management",
        description:
          "War room with timeline, AI hypotheses, similar incidents, and auto-generated post-mortem.",
      },
      {
        id: "executive",
        label: "Executive",
        title: "Executive Dashboard",
        description:
          "Consolidated weekly metrics: security, errors, support, reviews, incidents. Trend analysis and CSV export.",
      },
      {
        id: "security",
        label: "Security",
        title: "Security Analysis",
        description:
          "Static and DAST scanning with SSRF prevention. Audit log, rate limiting, and refresh tokens.",
      },
    ],
  },

  // Pricing
  pricing: {
    title: "Simple pricing, real value",
    subtitle: "Start with 7 free days. No credit card required.",
    earlyAdopter: "First 3 customers: $97/mo — price locked forever",
    plans: {
      pro: {
        name: "PRO",
        badge: "Most popular",
        price: "$97",
        period: "/mo",
        description:
          "Full Memora infrastructure. All modules, multi-repo, multi-user.",
        features: [
          "All 11 modules included",
          "Up to 50 repositories",
          "Unlimited users",
          "Email support",
          "Automatic updates",
          "7-day free trial",
        ],
        cta: "Start 7-day trial",
        note: "No credit card for trial",
        roi: "1 hour of senior dev time saved per day already pays for the plan",
      },
      enterprise: {
        name: "Enterprise",
        badge: "Maximum security",
        price: "$297",
        period: "/mo",
        description:
          "Database on your infrastructure. Full compliance, data never leaves your environment.",
        features: [
          "Everything in PRO",
          "Self-hosted database",
          "SSO (coming soon)",
          "Dedicated SLA",
          "Priority support",
          "GDPR on-premise",
          "Assisted setup",
        ],
        cta: "Talk to the team",
      },
      customer: {
        name: "Customer",
        badge: "Tailored",
        price: "Contact us",
        period: "",
        description:
          "Custom implementation of technical intelligence for your company's operations.",
        features: [
          "Implementation consulting",
          "Custom modules",
          "Integration with existing systems",
          "Team training",
          "Dedicated support",
          "Custom SLA",
        ],
        cta: "Talk to the team",
      },
    },
  },

  // FAQ
  faq: {
    title: "Frequently asked questions",
    items: [
      {
        q: "What is the 7-day trial?",
        a: "You get full access to all PRO plan modules for 7 days, no credit card required. If you like it, just subscribe. If not, your data is automatically removed.",
      },
      {
        q: "Where is my code stored?",
        a: "On the PRO plan, code is indexed and securely stored in Supabase (managed PostgreSQL with encryption at rest). On Enterprise, data stays 100% on your infrastructure.",
      },
      {
        q: "What's the difference between PRO and Enterprise?",
        a: "PRO uses Memora's managed infrastructure. Enterprise connects to your company's database — operational data never leaves your environment. Ideal for compliance and GDPR.",
      },
      {
        q: "Do I need technical knowledge to install?",
        a: "No. The guided onboarding takes less than 10 minutes: create account, configure LLM provider, connect GitHub, and index your first repository. All via web interface.",
      },
      {
        q: "Does it work with any programming language?",
        a: "Yes. Memora indexes any Git repository. AST analysis is optimized for Python, but the system works with JavaScript, TypeScript, Java, Go, Ruby, and other languages.",
      },
      {
        q: "What is the Customer plan?",
        a: "It's a custom implementation where Orbitalis adapts Memora to your company's operations: custom modules, integration with existing systems, training, and dedicated support.",
      },
      {
        q: "Can I cancel anytime?",
        a: "Yes. No lock-in. You can cancel at any time and your data will be removed within 30 days (or immediately, if you prefer).",
      },
      {
        q: "Which LLMs does Memora support?",
        a: "OpenAI (GPT-4o, GPT-4-turbo), Anthropic (Claude), Google (Gemini), Groq (Llama, Mixtral), and Ollama (local models). You choose the provider and model per organization.",
      },
    ],
  },

  // Final CTA
  cta: {
    headline: "Your system is ready to explain itself.",
    subheadline: "Start now. The first 7 days are on us.",
    button: "Start free trial",
  },

  // Footer
  footer: {
    tagline: "Operational Technical Intelligence",
    rights: "© 2026 Memora. All rights reserved.",
    product: "Product",
    pricing: "Pricing",
    enterprise: "Enterprise",
    customer: "Customer",
  },
} as const;
