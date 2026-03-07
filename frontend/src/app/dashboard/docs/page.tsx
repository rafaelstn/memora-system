"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  BookOpen,
  FileText,
  GraduationCap,
  Loader2,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/hooks/useAuth";
import { listRepos, getDocsStatus, getOnboardingProgress } from "@/lib/api";
import type { RepoDocStatus, OnboardingProgress } from "@/lib/types";

interface RepoInfo {
  name: string;
  chunks_count: number;
  last_indexed?: string;
  status: string;
}

interface RepoWithDocs extends RepoInfo {
  docs?: RepoDocStatus;
  onboarding?: OnboardingProgress;
}

export default function DocsIndexPage() {
  const { user } = useAuth();
  const [repos, setRepos] = useState<RepoWithDocs[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        const repoList = await listRepos();
        // Load docs status for each repo
        const enriched = await Promise.all(
          repoList.map(async (repo: RepoInfo) => {
            let docs: RepoDocStatus | undefined;
            let onboarding: OnboardingProgress | undefined;
            try {
              docs = await getDocsStatus(repo.name);
            } catch {}
            try {
              onboarding = await getOnboardingProgress(repo.name);
            } catch {}
            return { ...repo, docs, onboarding };
          }),
        );
        setRepos(enriched);
      } catch {}
      setLoading(false);
    })();
  }, [user]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-accent" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center gap-3 mb-6">
        <BookOpen className="h-6 w-6 text-accent" />
        <h1 className="text-2xl font-bold">Documentacao Automatica</h1>
      </div>

      <p className="text-sm text-muted mb-6">
        Gere README e guias de onboarding automaticamente a partir do codigo indexado.
      </p>

      {repos.length === 0 ? (
        <div className="text-center py-16">
          <BookOpen className="h-12 w-12 text-muted mx-auto mb-3" />
          <p className="text-sm font-medium">Nenhum repositorio indexado</p>
          <p className="text-xs text-muted mt-1">Indexe um repositorio primeiro para gerar documentacao.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {repos.map((repo) => (
            <Link
              key={repo.name}
              href={`/dashboard/docs/${encodeURIComponent(repo.name)}`}
              className="flex items-center gap-4 p-4 rounded-xl border border-border bg-card-bg hover:border-accent/40 hover:bg-hover transition-colors group"
            >
              <div className="h-10 w-10 rounded-xl bg-accent-surface flex items-center justify-center shrink-0">
                <BookOpen className="h-5 w-5 text-accent" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{repo.name}</p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-xs text-muted flex items-center gap-1">
                    <FileText className="h-3 w-3" />
                    {repo.docs?.readme ? (
                      <span className="text-success">README gerado</span>
                    ) : (
                      "README nao gerado"
                    )}
                  </span>
                  <span className="text-xs text-muted flex items-center gap-1">
                    <GraduationCap className="h-3 w-3" />
                    {repo.onboarding?.started ? (
                      <span className="text-accent">{repo.onboarding.steps_completed}/{repo.onboarding.steps_total} passos</span>
                    ) : repo.docs?.onboarding_guide ? (
                      <span className="text-success">Guia gerado</span>
                    ) : (
                      "Guia nao gerado"
                    )}
                  </span>
                </div>
              </div>
              <ChevronRight className="h-4 w-4 text-muted group-hover:text-foreground transition-colors shrink-0" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
