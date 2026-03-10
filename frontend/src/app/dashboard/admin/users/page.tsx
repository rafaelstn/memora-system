"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Search,
  UserPlus,
  Copy,
  UserX,
  UserCheck,
  Trash2,
  Loader2,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import { RoleBadge, StatusBadge } from "@/components/ui/badge";
import { Modal } from "@/components/ui/modal";
import type { Role, Product } from "@/lib/types";
import {
  listUsers,
  updateUserRole,
  toggleUserActive,
  listInvites,
  createInvite,
  revokeInviteApi,
  listProducts,
} from "@/lib/api";

interface UserRow {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_activity?: string;
}

interface InviteRow {
  id: string;
  token: string;
  role: string;
  email?: string;
  product_id?: string;
  created_at: string;
  expires_at: string;
  status: string;
}

export default function UsersPage() {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [invites, setInvites] = useState<InviteRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [roleFilter, setRoleFilter] = useState<Role | "all">("all");
  const [search, setSearch] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<Role>("dev");
  const [inviteProductId, setInviteProductId] = useState<string>("");
  const [generatedLink, setGeneratedLink] = useState<string | null>(null);
  const [inviteLoading, setInviteLoading] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [usersData, invitesData, productsData] = await Promise.all([
        listUsers(
          roleFilter !== "all" ? roleFilter : undefined,
          search || undefined,
        ),
        listInvites(),
        listProducts().catch(() => []),
      ]);
      setUsers(usersData);
      setInvites(invitesData);
      setProducts(productsData);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  }, [roleFilter, search]);

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => fetchData(), 300);
    return () => clearTimeout(timer);
  }, [fetchData]);

  async function handleRoleChange(userId: string, newRole: Role) {
    try {
      await updateUserRole(userId, newRole);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u)),
      );
      toast.success("Role atualizada com sucesso");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao atualizar role");
    }
  }

  async function handleToggleActive(userId: string) {
    try {
      await toggleUserActive(userId);
      setUsers((prev) =>
        prev.map((u) =>
          u.id === userId ? { ...u, is_active: !u.is_active } : u,
        ),
      );
      toast.success("Status do usuário atualizado");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao atualizar status");
    }
  }

  async function handleInvite() {
    setInviteLoading(true);
    try {
      const result = await createInvite(inviteRole, inviteEmail || undefined, inviteProductId || undefined);
      setGeneratedLink(result.invite_url);
      setInvites((prev) => [
        {
          id: result.id,
          token: result.token,
          role: result.role,
          email: inviteEmail || undefined,
          created_at: new Date().toISOString(),
          expires_at: result.expires_at,
          status: "pending",
        },
        ...prev,
      ]);
      toast.success("Convite criado com sucesso!");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao criar convite");
    } finally {
      setInviteLoading(false);
    }
  }

  function copyLink() {
    if (generatedLink) {
      navigator.clipboard.writeText(generatedLink);
      toast.success("Link copiado!");
    }
  }

  async function handleRevokeInvite(inviteId: string) {
    try {
      await revokeInviteApi(inviteId);
      setInvites((prev) => prev.filter((inv) => inv.id !== inviteId));
      toast.success("Convite revogado");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao revogar convite");
    }
  }

  function closeInviteModal() {
    setInviteOpen(false);
    setInviteEmail("");
    setInviteRole("dev");
    setInviteProductId("");
    setGeneratedLink(null);
  }

  return (
    <div className="p-5 lg:p-8 space-y-8">
      <div className="flex items-center justify-between pt-2">
        <h1 className="text-xl font-semibold">Gerenciar Usuários</h1>
        <button
          onClick={() => setInviteOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors"
        >
          <UserPlus size={16} />
          Convidar
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value as Role | "all")}
          className="px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground"
        >
          <option value="all">Todos</option>
          <option value="admin">Admin</option>
          <option value="dev">Dev</option>
          <option value="suporte">Suporte</option>
        </select>
        <div className="relative flex-1 max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Buscar por nome ou email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted"
          />
        </div>
      </div>

      {/* Users List */}
      <div className="rounded-xl border border-border bg-card-bg divide-y divide-border">
        {loading && (
          <div className="flex items-center justify-center gap-2 px-6 py-12 text-muted text-sm">
            <Loader2 size={16} className="animate-spin" />
            Carregando...
          </div>
        )}
        {!loading && users.length === 0 && (
          <div className="px-6 py-12 text-center text-muted text-sm">
            Nenhum usuário encontrado.
          </div>
        )}
        {!loading &&
          users.map((user) => (
            <div
              key={user.id}
              className={cn(
                "flex items-center gap-4 px-6 py-4",
                !user.is_active && "opacity-50",
              )}
            >
              <div className="w-10 h-10 rounded-full bg-accent-surface text-accent-text flex items-center justify-center font-semibold text-sm shrink-0">
                {user.name.charAt(0).toUpperCase()}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm truncate">{user.name}</span>
                  <RoleBadge role={user.role as Role} />
                  {!user.is_active && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-danger-surface text-danger">
                      Inativo
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted truncate">{user.email}</p>
                <p className="text-xs text-muted mt-0.5">
                  Entrou em{" "}
                  {new Date(user.created_at).toLocaleDateString("pt-BR")}
                  {user.last_activity && (
                    <>
                      {" "}
                      · Último acesso:{" "}
                      {new Date(user.last_activity).toLocaleDateString("pt-BR")}
                    </>
                  )}
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <select
                  value={user.role}
                  onChange={(e) =>
                    handleRoleChange(user.id, e.target.value as Role)
                  }
                  className="px-2 py-1 text-xs rounded-md border border-border bg-card-bg text-foreground"
                >
                  <option value="admin">admin</option>
                  <option value="dev">dev</option>
                  <option value="suporte">suporte</option>
                </select>
                <button
                  onClick={() => handleToggleActive(user.id)}
                  className={cn(
                    "p-1.5 rounded-lg border border-border hover:bg-hover transition-colors",
                    user.is_active ? "text-danger" : "text-success",
                  )}
                  title={user.is_active ? "Desativar" : "Ativar"}
                >
                  {user.is_active ? (
                    <UserX size={14} />
                  ) : (
                    <UserCheck size={14} />
                  )}
                </button>
              </div>
            </div>
          ))}
      </div>

      {/* Pending Invites */}
      <div className="mt-8">
        <h2 className="text-base font-semibold mb-4">Convites pendentes</h2>
        <div className="rounded-lg border border-border bg-card-bg overflow-hidden">
          <table className="w-full">
            <thead className="border-b border-border bg-hover">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                  Token
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                  Role
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                  Email
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                  Criado em
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                  Expira em
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                  Ação
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {invites.map((inv) => (
                <tr key={inv.id} className="hover:bg-hover">
                  <td className="px-4 py-3 text-sm font-mono">
                    {inv.token.slice(0, 8)}...
                  </td>
                  <td className="px-4 py-3">
                    <RoleBadge role={inv.role as Role} />
                  </td>
                  <td className="px-4 py-3 text-sm text-muted">
                    {inv.email || "—"}
                  </td>
                  <td className="px-4 py-3 text-sm text-muted">
                    {new Date(inv.created_at).toLocaleDateString("pt-BR")}
                  </td>
                  <td className="px-4 py-3 text-sm text-muted">
                    {new Date(inv.expires_at).toLocaleDateString("pt-BR")}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={inv.status} />
                  </td>
                  <td className="px-4 py-3">
                    {inv.status === "pending" && (
                      <button
                        onClick={() => handleRevokeInvite(inv.id)}
                        className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-lg text-danger hover:bg-danger-surface transition-colors"
                      >
                        <Trash2 size={12} />
                        Revogar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {invites.length === 0 && (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-8 text-center text-sm text-muted"
                  >
                    Nenhum convite encontrado.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invite Modal */}
      <Modal
        open={inviteOpen}
        onClose={closeInviteModal}
        title="Convidar Usuário"
      >
        {!generatedLink ? (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Email (opcional)
              </label>
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="usuario@empresa.com"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Role *</label>
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value as Role)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground"
              >
                <option value="admin">Admin</option>
                <option value="dev">Dev</option>
                <option value="suporte">Suporte</option>
              </select>
            </div>
            {products.length > 0 && (
              <div>
                <label className="block text-sm font-medium mb-1">
                  Produto (opcional)
                </label>
                <select
                  value={inviteProductId}
                  onChange={(e) => setInviteProductId(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground"
                >
                  <option value="">Nenhum — acesso definido depois</option>
                  {products.filter((p) => p.is_active).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted mt-1">
                  O usuario sera automaticamente adicionado como membro do produto selecionado.
                </p>
              </div>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={closeInviteModal}
                className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-hover transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleInvite}
                disabled={inviteLoading}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
              >
                {inviteLoading && (
                  <Loader2 size={14} className="animate-spin" />
                )}
                Gerar convite
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Link de convite gerado com sucesso:
            </p>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={generatedLink}
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground font-mono text-xs"
              />
              <button
                onClick={copyLink}
                className="p-2 rounded-lg border border-border hover:bg-hover transition-colors"
                title="Copiar"
              >
                <Copy size={16} />
              </button>
            </div>
            <div className="flex justify-end pt-2">
              <button
                onClick={closeInviteModal}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors"
              >
                Fechar
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
