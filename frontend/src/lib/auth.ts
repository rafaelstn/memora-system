import type { Role } from "./types";
import { createClient } from "./supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function signIn(email: string, password: string) {
  const supabase = createClient();
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });
  if (error) throw error;
  return data;
}

export async function signUp(
  name: string,
  email: string,
  password: string,
  inviteToken?: string,
  orgName?: string,
) {
  const supabase = createClient();

  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "ngrok-skip-browser-warning": "true" },
    body: JSON.stringify({
      name,
      email,
      password,
      invite_token: inviteToken || null,
      org_name: orgName || null,
    }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Erro ${res.status}`);
  }

  const user = await res.json();

  // Login automático após registro
  await supabase.auth.signInWithPassword({ email, password });

  return user;
}

export async function signOut() {
  const supabase = createClient();
  await supabase.auth.signOut();
}

export async function resetPassword(email: string) {
  const supabase = createClient();
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${window.location.origin}/auth/update-password`,
  });
  if (error) throw error;
}

export async function updatePassword(newPassword: string) {
  const supabase = createClient();
  const { error } = await supabase.auth.updateUser({ password: newPassword });
  if (error) throw error;
}

export async function getSession() {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  return data.session;
}

export async function getAccessToken(): Promise<string | null> {
  const session = await getSession();
  return session?.access_token ?? null;
}

export async function fetchUserProfile(): Promise<{
  id: string;
  name: string;
  email: string;
  role: Role;
  avatar_url: string | null;
  is_active: boolean;
  github_connected: boolean;
  org_id: string;
  org_name: string | null;
  onboarding_completed: boolean;
  onboarding_step: number;
} | null> {
  const token = await getAccessToken();
  if (!token) return null;

  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}`, "ngrok-skip-browser-warning": "true" },
  });
  if (!res.ok) return null;
  return res.json();
}
