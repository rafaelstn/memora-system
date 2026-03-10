"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { apiFetch } from "@/lib/api";

export interface SearchResultItem {
  id: string;
  title: string;
  preview: string;
  source: string;
  source_label: string;
  created_at: string;
  url: string;
}

export interface GlobalSearchResults {
  results: Record<string, SearchResultItem[]>;
  total: number;
  query: string;
}

export function useGlobalSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GlobalSearchResults | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const search = useCallback(async (q: string) => {
    if (!q || q.trim().length < 2) {
      setResults(null);
      return;
    }

    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();

    setIsLoading(true);
    setError(null);

    try {
      const data = await apiFetch<GlobalSearchResults>(
        `/api/search/global?q=${encodeURIComponent(q.trim())}&limit=3`
      );
      setResults(data);
      // Add to recent searches
      setRecentSearches((prev) => {
        const filtered = prev.filter((s) => s !== q.trim());
        return [q.trim(), ...filtered].slice(0, 5);
      });
    } catch (err: any) {
      if (err?.name !== "AbortError") {
        setError("Erro ao buscar. Tente novamente.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const debouncedSearch = useCallback(
    (q: string) => {
      setQuery(q);
      if (timerRef.current) clearTimeout(timerRef.current);
      if (!q || q.trim().length < 2) {
        setResults(null);
        return;
      }
      timerRef.current = setTimeout(() => search(q), 300);
    },
    [search]
  );

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  const reset = useCallback(() => {
    setQuery("");
    setResults(null);
    setError(null);
  }, []);

  return {
    query,
    results,
    isLoading,
    error,
    recentSearches,
    debouncedSearch,
    reset,
  };
}
