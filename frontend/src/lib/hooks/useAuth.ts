"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import type { Role } from "@/lib/types";
import { createClient } from "@/lib/supabase";
import { fetchUserProfile, signOut as authSignOut } from "@/lib/auth";

interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatar_url: string | null;
  is_active: boolean;
  github_connected: boolean;
  org_id: string;
  org_name: string | null;
  org_mode: "saas" | "enterprise";
  enterprise_setup_complete: boolean;
  onboarding_completed: boolean;
  onboarding_step: number;
}

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const supabase = createClient();

  const loadUser = useCallback(async () => {
    setIsLoading(true);
    try {
      const { data } = await supabase.auth.getSession();
      if (!data.session) {
        setUser(null);
        return;
      }
      const profile = await fetchUserProfile();
      setUser(profile);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (session) {
          loadUser();
        } else {
          setUser(null);
          setIsLoading(false);
        }
      },
    );

    return () => subscription.unsubscribe();
  }, [loadUser]);

  const signOut = useCallback(async () => {
    await authSignOut();
    setUser(null);
    router.push("/auth/signin");
  }, [router]);

  return {
    user,
    role: user?.role ?? null,
    isLoading,
    isAuthenticated: !!user,
    signOut,
    refreshUser: loadUser,
  };
}
