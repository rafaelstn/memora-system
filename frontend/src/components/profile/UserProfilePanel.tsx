"use client";

import { useState, useRef } from "react";
import { Modal } from "@/components/ui/modal";
import { RoleBadge } from "@/components/ui/badge";
import { updateProfile, changePassword } from "@/lib/api";
import {
  Camera,
  Check,
  Eye,
  EyeOff,
  Loader2,
  Mail,
  Shield,
  User as UserIcon,
  Calendar,
  Building2,
} from "lucide-react";
import type { Role } from "@/lib/types";

interface ProfileUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatar_url: string | null;
  org_name: string | null;
  created_at?: string | null;
}

interface UserProfilePanelProps {
  open: boolean;
  onClose: () => void;
  user: ProfileUser;
  onProfileUpdated: () => void;
}

export function UserProfilePanel({ open, onClose, user, onProfileUpdated }: UserProfilePanelProps) {
  const [tab, setTab] = useState<"info" | "password">("info");
  const [name, setName] = useState(user.name);
  const [avatarUrl, setAvatarUrl] = useState(user.avatar_url || "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordChanged, setPasswordChanged] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSaveProfile = async () => {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const updates: Record<string, string> = {};
      if (name.trim() !== user.name) updates.name = name.trim();
      if (avatarUrl !== (user.avatar_url || "")) updates.avatar_url = avatarUrl;
      if (Object.keys(updates).length === 0) {
        setSaving(false);
        return;
      }
      await updateProfile(updates);
      setSaved(true);
      onProfileUpdated();
      setTimeout(() => setSaved(false), 2000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erro ao salvar perfil");
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    setPasswordError("");
    if (newPassword.length < 6) {
      setPasswordError("Senha deve ter no minimo 6 caracteres");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("As senhas nao coincidem");
      return;
    }
    setChangingPassword(true);
    setPasswordChanged(false);
    try {
      await changePassword(newPassword);
      setPasswordChanged(true);
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => setPasswordChanged(false), 3000);
    } catch (e: unknown) {
      setPasswordError(e instanceof Error ? e.message : "Erro ao alterar senha");
    } finally {
      setChangingPassword(false);
    }
  };

  const handleAvatarFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Selecione um arquivo de imagem");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setError("Imagem deve ter no maximo 2MB");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setAvatarUrl(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const initials = user.name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <Modal open={open} onClose={onClose} title="Meu Perfil">
      <div className="space-y-5">
        {/* Avatar + basic info */}
        <div className="flex items-center gap-4">
          <div className="relative group">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt={user.name}
                className="h-16 w-16 rounded-full object-cover border-2 border-border"
              />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent-surface text-accent-text text-xl font-bold border-2 border-border">
                {initials}
              </div>
            )}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="absolute inset-0 flex items-center justify-center rounded-full bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <Camera size={18} className="text-white" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleAvatarFileChange}
            />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-lg font-semibold truncate">{user.name}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <RoleBadge role={user.role} />
              {user.org_name && (
                <span className="text-xs text-muted flex items-center gap-1">
                  <Building2 size={11} />
                  {user.org_name}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border">
          <button
            onClick={() => setTab("info")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === "info"
                ? "border-accent-text text-accent-text"
                : "border-transparent text-muted hover:text-foreground"
            }`}
          >
            Informacoes
          </button>
          <button
            onClick={() => setTab("password")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === "password"
                ? "border-accent-text text-accent-text"
                : "border-transparent text-muted hover:text-foreground"
            }`}
          >
            Alterar Senha
          </button>
        </div>

        {tab === "info" && (
          <div className="space-y-4">
            {/* Name */}
            <div>
              <label className="flex items-center gap-1.5 text-xs font-medium text-muted mb-1.5">
                <UserIcon size={12} />
                Nome
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-text/30"
              />
            </div>

            {/* Email (read-only) */}
            <div>
              <label className="flex items-center gap-1.5 text-xs font-medium text-muted mb-1.5">
                <Mail size={12} />
                Email
              </label>
              <input
                type="email"
                value={user.email}
                disabled
                className="w-full rounded-lg border border-border bg-hover/50 px-3 py-2 text-sm text-muted cursor-not-allowed"
              />
            </div>

            {/* Role (read-only) */}
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="flex items-center gap-1.5 text-xs font-medium text-muted mb-1.5">
                  <Shield size={12} />
                  Cargo
                </label>
                <div className="rounded-lg border border-border bg-hover/50 px-3 py-2 text-sm text-muted">
                  {user.role === "admin" ? "Administrador" : user.role === "dev" ? "Desenvolvedor" : "Suporte"}
                </div>
              </div>
              {user.created_at && (
                <div className="flex-1">
                  <label className="flex items-center gap-1.5 text-xs font-medium text-muted mb-1.5">
                    <Calendar size={12} />
                    Membro desde
                  </label>
                  <div className="rounded-lg border border-border bg-hover/50 px-3 py-2 text-sm text-muted">
                    {new Date(user.created_at).toLocaleDateString("pt-BR")}
                  </div>
                </div>
              )}
            </div>

            {/* Avatar URL (optional manual input) */}
            <div>
              <label className="flex items-center gap-1.5 text-xs font-medium text-muted mb-1.5">
                <Camera size={12} />
                URL do Avatar (opcional)
              </label>
              <input
                type="url"
                value={avatarUrl}
                onChange={(e) => setAvatarUrl(e.target.value)}
                placeholder="https://..."
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-text/30"
              />
            </div>

            {error && (
              <p className="text-xs text-red-500">{error}</p>
            )}

            <button
              onClick={handleSaveProfile}
              disabled={saving}
              className="flex items-center justify-center gap-2 w-full rounded-lg bg-accent-surface px-4 py-2.5 text-sm font-medium text-accent-text hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {saving ? (
                <Loader2 size={14} className="animate-spin" />
              ) : saved ? (
                <Check size={14} />
              ) : null}
              {saved ? "Salvo!" : "Salvar Alteracoes"}
            </button>
          </div>
        )}

        {tab === "password" && (
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-muted mb-1.5 block">
                Nova Senha
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Minimo 6 caracteres"
                  className="w-full rounded-lg border border-border bg-transparent px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-accent-text/30"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted hover:text-foreground"
                >
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-muted mb-1.5 block">
                Confirmar Senha
              </label>
              <input
                type={showPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repita a nova senha"
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-text/30"
              />
            </div>

            {passwordError && (
              <p className="text-xs text-red-500">{passwordError}</p>
            )}

            {passwordChanged && (
              <p className="text-xs text-green-500 flex items-center gap-1">
                <Check size={12} />
                Senha alterada com sucesso!
              </p>
            )}

            <button
              onClick={handleChangePassword}
              disabled={changingPassword || !newPassword}
              className="flex items-center justify-center gap-2 w-full rounded-lg bg-accent-surface px-4 py-2.5 text-sm font-medium text-accent-text hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {changingPassword && <Loader2 size={14} className="animate-spin" />}
              Alterar Senha
            </button>
          </div>
        )}
      </div>
    </Modal>
  );
}
