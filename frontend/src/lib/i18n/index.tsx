"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { pt, type Translations } from "./pt";
import { en } from "./en";

type Locale = "pt" | "en";

interface I18nContextValue {
  locale: Locale;
  t: Translations;
  toggleLocale: () => void;
}

const translations: Record<Locale, Translations> = { pt, en };

const I18nContext = createContext<I18nContextValue>({
  locale: "pt",
  t: pt,
  toggleLocale: () => {},
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>("pt");

  const toggleLocale = useCallback(() => {
    setLocale((prev) => (prev === "pt" ? "en" : "pt"));
  }, []);

  return (
    <I18nContext.Provider value={{ locale, t: translations[locale], toggleLocale }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}
