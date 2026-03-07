export function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) return "Hoje";
  if (days === 1) return "Ontem";
  if (days <= 7) return "Últimos 7 dias";
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

export function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatCurrency(value: number, currency = "BRL"): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(value);
}

export function formatCostUSD(value: number): string {
  return `$${value.toFixed(6)}`;
}

export function groupByDate<T extends { created_at: string }>(
  items: T[],
): Record<string, T[]> {
  const groups: Record<string, T[]> = {};
  for (const item of items) {
    const label = formatDate(item.created_at);
    if (!groups[label]) groups[label] = [];
    groups[label].push(item);
  }
  return groups;
}

export function truncate(str: string, maxWords: number): string {
  const words = str.split(/\s+/);
  if (words.length <= maxWords) return str;
  return words.slice(0, maxWords).join(" ") + "...";
}

export function cn(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(" ");
}
