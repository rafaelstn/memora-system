"use client";

import { useProduct } from "@/lib/product-context";
import { Package } from "lucide-react";

export function ProductSelector() {
  const { products, showSelector, selectProduct, activeProduct } = useProduct();

  if (!showSelector) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div
        className="w-full max-w-md rounded-2xl border border-border bg-card-bg"
        style={{ boxShadow: "var(--shadow-lg)" }}
      >
        <div className="border-b border-border px-6 py-4">
          <h3 className="text-lg font-semibold">Selecione um produto</h3>
          <p className="mt-1 text-sm text-muted">
            Escolha o produto em que deseja trabalhar.
          </p>
        </div>

        <div className="px-6 py-5 space-y-2 max-h-80 overflow-y-auto">
          {products.length === 0 ? (
            <p className="text-sm text-muted text-center py-8">
              Nenhum produto disponível. Peça a um administrador para criar um.
            </p>
          ) : (
            products.map((product) => (
              <button
                key={product.id}
                onClick={() => selectProduct(product)}
                className={`w-full flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition-colors ${
                  activeProduct?.id === product.id
                    ? "border-accent bg-accent-surface"
                    : "border-border hover:border-accent/50 hover:bg-hover"
                }`}
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-surface text-accent-text">
                  <Package size={18} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{product.name}</p>
                  {product.description && (
                    <p className="mt-0.5 text-xs text-muted line-clamp-2">
                      {product.description}
                    </p>
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
