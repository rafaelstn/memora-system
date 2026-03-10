"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Package,
  Plus,
  Pencil,
  Archive,
  Loader2,
  Users,
  UserPlus,
  Trash2,
} from "lucide-react";
import toast from "react-hot-toast";
import { Modal } from "@/components/ui/modal";
import { cn } from "@/lib/utils";
import { useProduct } from "@/lib/product-context";
import type { Product, ProductMember } from "@/lib/types";
import {
  listProducts,
  createProduct,
  updateProduct,
  archiveProduct,
  listProductMembers,
  addProductMember,
  removeProductMember,
} from "@/lib/api";

export default function ProdutosPage() {
  const { refreshProducts } = useProduct();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  // Create/Edit modal
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [saving, setSaving] = useState(false);

  // Members modal
  const [membersProduct, setMembersProduct] = useState<Product | null>(null);
  const [members, setMembers] = useState<ProductMember[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [addEmail, setAddEmail] = useState("");
  const [addingMember, setAddingMember] = useState(false);

  const fetchProducts = useCallback(async () => {
    try {
      const data = await listProducts();
      setProducts(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao carregar produtos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const openCreate = () => {
    setEditingProduct(null);
    setFormName("");
    setFormDesc("");
    setModalOpen(true);
  };

  const openEdit = (product: Product) => {
    setEditingProduct(product);
    setFormName(product.name);
    setFormDesc(product.description || "");
    setModalOpen(true);
  };

  const handleSave = async () => {
    if (!formName.trim()) {
      toast.error("Nome é obrigatório");
      return;
    }
    setSaving(true);
    try {
      if (editingProduct) {
        await updateProduct(editingProduct.id, {
          name: formName.trim(),
          description: formDesc.trim() || undefined,
        });
        toast.success("Produto atualizado");
      } else {
        await createProduct({
          name: formName.trim(),
          description: formDesc.trim() || undefined,
        });
        toast.success("Produto criado");
      }
      setModalOpen(false);
      fetchProducts();
      refreshProducts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  };

  const handleArchive = async (product: Product) => {
    if (!confirm(`Arquivar o produto "${product.name}"?`)) return;
    try {
      await archiveProduct(product.id);
      toast.success("Produto arquivado");
      fetchProducts();
      refreshProducts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao arquivar");
    }
  };

  const openMembers = async (product: Product) => {
    setMembersProduct(product);
    setMembersLoading(true);
    setMembers([]);
    setAddEmail("");
    try {
      const data = await listProductMembers(product.id);
      setMembers(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao carregar membros");
    } finally {
      setMembersLoading(false);
    }
  };

  const handleAddMember = async () => {
    if (!membersProduct || !addEmail.trim()) return;
    setAddingMember(true);
    try {
      await addProductMember(membersProduct.id, addEmail.trim());
      toast.success("Membro adicionado");
      setAddEmail("");
      const data = await listProductMembers(membersProduct.id);
      setMembers(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao adicionar");
    } finally {
      setAddingMember(false);
    }
  };

  const handleRemoveMember = async (membershipId: string) => {
    if (!membersProduct) return;
    try {
      await removeProductMember(membersProduct.id, membershipId);
      toast.success("Membro removido");
      setMembers((prev) => prev.filter((m) => m.id !== membershipId));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao remover");
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Produtos</h1>
          <p className="mt-1 text-sm text-muted">
            Gerencie os produtos da organização.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90 transition-colors"
        >
          <Plus size={16} />
          Novo produto
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={24} className="animate-spin text-muted" />
        </div>
      ) : products.length === 0 ? (
        <div className="rounded-xl border border-border bg-card-bg p-12 text-center">
          <Package size={40} className="mx-auto text-muted" />
          <p className="mt-3 text-sm text-muted">Nenhum produto cadastrado.</p>
          <button
            onClick={openCreate}
            className="mt-4 text-sm font-medium text-accent-text hover:underline"
          >
            Criar primeiro produto
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {products.map((product) => (
            <div
              key={product.id}
              className={cn(
                "flex items-center gap-4 rounded-xl border border-border bg-card-bg px-5 py-4 transition-colors",
                !product.is_active && "opacity-50"
              )}
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-surface text-accent-text">
                <Package size={20} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold truncate">{product.name}</p>
                  {!product.is_active && (
                    <span className="rounded-full bg-yellow-500/10 px-2 py-0.5 text-[10px] font-medium text-yellow-600">
                      Arquivado
                    </span>
                  )}
                </div>
                {product.description && (
                  <p className="mt-0.5 text-xs text-muted truncate">
                    {product.description}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => openMembers(product)}
                  className="p-2 rounded-lg hover:bg-hover text-muted hover:text-foreground transition-colors"
                  title="Membros"
                >
                  <Users size={16} />
                </button>
                <button
                  onClick={() => openEdit(product)}
                  className="p-2 rounded-lg hover:bg-hover text-muted hover:text-foreground transition-colors"
                  title="Editar"
                >
                  <Pencil size={16} />
                </button>
                {product.is_active && (
                  <button
                    onClick={() => handleArchive(product)}
                    className="p-2 rounded-lg hover:bg-hover text-muted hover:text-red-500 transition-colors"
                    title="Arquivar"
                  >
                    <Archive size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingProduct ? "Editar produto" : "Novo produto"}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">Nome</label>
            <input
              type="text"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="Ex: Plataforma Web"
              className="w-full rounded-lg border border-border bg-input-bg px-3 py-2 text-sm outline-none focus:border-accent transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">
              Descrição <span className="text-muted">(opcional)</span>
            </label>
            <textarea
              value={formDesc}
              onChange={(e) => setFormDesc(e.target.value)}
              placeholder="Breve descrição do produto..."
              rows={3}
              className="w-full rounded-lg border border-border bg-input-bg px-3 py-2 text-sm outline-none focus:border-accent transition-colors resize-none"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={() => setModalOpen(false)}
              className="rounded-lg px-4 py-2 text-sm font-medium text-muted hover:bg-hover transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90 transition-colors disabled:opacity-50"
            >
              {saving && <Loader2 size={14} className="animate-spin" />}
              {editingProduct ? "Salvar" : "Criar"}
            </button>
          </div>
        </div>
      </Modal>

      {/* Members Modal */}
      <Modal
        open={!!membersProduct}
        onClose={() => setMembersProduct(null)}
        title={`Membros — ${membersProduct?.name || ""}`}
      >
        <div className="space-y-4">
          {/* Add member */}
          <div className="flex gap-2">
            <input
              type="email"
              value={addEmail}
              onChange={(e) => setAddEmail(e.target.value)}
              placeholder="email@exemplo.com"
              className="flex-1 rounded-lg border border-border bg-input-bg px-3 py-2 text-sm outline-none focus:border-accent transition-colors"
              onKeyDown={(e) => e.key === "Enter" && handleAddMember()}
            />
            <button
              onClick={handleAddMember}
              disabled={addingMember || !addEmail.trim()}
              className="flex items-center gap-1.5 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent/90 transition-colors disabled:opacity-50"
            >
              {addingMember ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <UserPlus size={14} />
              )}
              Adicionar
            </button>
          </div>

          {/* Members list */}
          {membersLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 size={20} className="animate-spin text-muted" />
            </div>
          ) : members.length === 0 ? (
            <p className="text-center text-sm text-muted py-6">
              Nenhum membro neste produto.
            </p>
          ) : (
            <div className="max-h-60 space-y-2 overflow-y-auto">
              {members.map((member) => (
                <div
                  key={member.id}
                  className="flex items-center gap-3 rounded-lg border border-border px-3 py-2.5"
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-surface text-accent-text text-xs font-semibold">
                    {member.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">{member.name}</p>
                    <p className="text-xs text-muted truncate">{member.email}</p>
                  </div>
                  <button
                    onClick={() => handleRemoveMember(member.id)}
                    className="p-1.5 rounded-lg hover:bg-hover text-muted hover:text-red-500 transition-colors"
                    title="Remover"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}
