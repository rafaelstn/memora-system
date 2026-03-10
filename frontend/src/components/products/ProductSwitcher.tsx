"use client";

import { useState, useRef, useEffect } from "react";
import { useProduct } from "@/lib/product-context";
import { Package, ChevronDown, Check } from "lucide-react";

export function ProductSwitcher() {
  const { products, activeProduct, selectProduct, openSelector } = useProduct();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  if (!activeProduct) return null;

  // Single product — just show indicator, no dropdown
  if (products.length <= 1) {
    return (
      <div className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted">
        <Package size={14} />
        <span className="truncate font-medium text-foreground">
          {activeProduct.name}
        </span>
      </div>
    );
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-hover transition-colors"
      >
        <Package size={14} className="shrink-0 text-accent-text" />
        <span className="truncate font-medium">{activeProduct.name}</span>
        <ChevronDown
          size={14}
          className={`ml-auto shrink-0 text-muted transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div
          className="absolute left-0 right-0 top-full z-50 mt-1 rounded-xl border border-border bg-card-bg py-1"
          style={{ boxShadow: "var(--shadow-md)" }}
        >
          {products.map((product) => (
            <button
              key={product.id}
              onClick={() => {
                selectProduct(product);
                setOpen(false);
              }}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-hover transition-colors"
            >
              <span className="truncate flex-1 text-left">{product.name}</span>
              {product.id === activeProduct.id && (
                <Check size={14} className="shrink-0 text-accent-text" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
