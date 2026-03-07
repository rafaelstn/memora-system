import type { Metadata } from "next";
import { Toaster } from "react-hot-toast";
import { ThemeProvider } from "@/components/theme-provider";
import { ChatProvider } from "@/lib/chat-context";
import "./globals.css";

export const metadata: Metadata = {
  title: "Memora — Inteligência Técnica Operacional",
  description:
    "Assistente técnico interno que aprende o seu codebase e responde em português",
  openGraph: {
    title: "Memora — Inteligência Técnica Operacional",
    description:
      "Assistente técnico interno que aprende o seu codebase e responde em português",
    type: "website",
  },
  icons: {
    icon: "/icon.png",
    apple: "/icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="antialiased">
        <ThemeProvider>
          <ChatProvider>
          {children}
          </ChatProvider>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                borderRadius: "10px",
                background: "var(--card-bg)",
                color: "var(--foreground)",
                border: "1px solid var(--border)",
                boxShadow: "var(--shadow-md)",
                fontSize: "14px",
              },
            }}
          />
        </ThemeProvider>
      </body>
    </html>
  );
}
