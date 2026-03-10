"use client";

import {
  createContext,
  useContext,
  useCallback,
  useState,
  useEffect,
  useRef,
} from "react";
import type { Product } from "./types";
import { listProducts, setActiveProductId } from "./api";
import { useAuth } from "./hooks/useAuth";

interface ProductContextValue {
  /** All products the user has access to */
  products: Product[];
  /** Currently active product */
  activeProduct: Product | null;
  /** Whether products are still loading */
  isLoading: boolean;
  /** Whether the product selector should be shown */
  showSelector: boolean;
  /** Set active product */
  selectProduct: (product: Product) => void;
  /** Open the product selector modal */
  openSelector: () => void;
  /** Close the product selector modal */
  closeSelector: () => void;
  /** Refresh products list from API */
  refreshProducts: () => Promise<void>;
}

const ProductContext = createContext<ProductContextValue | null>(null);

export function ProductProvider({ children }: { children: React.ReactNode }) {
  const { user, isLoading: authLoading } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [activeProduct, setActiveProduct] = useState<Product | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showSelector, setShowSelector] = useState(false);
  const loadedRef = useRef(false);

  const loadProducts = useCallback(async () => {
    try {
      const list = await listProducts();
      const active = list.filter((p) => p.is_active);
      setProducts(active);

      // Auto-select if single product
      if (active.length === 1 && !activeProduct) {
        setActiveProduct(active[0]);
        setActiveProductId(active[0].id);
      } else if (active.length > 1 && !activeProduct) {
        // Multiple products — show selector
        setShowSelector(true);
      } else if (active.length === 0) {
        // No products (admin may need to create one)
        setActiveProduct(null);
        setActiveProductId(null);
      }
    } catch {
      // API may fail if user is not authenticated yet
      setProducts([]);
    } finally {
      setIsLoading(false);
    }
  }, [activeProduct]);

  // Load products when user is authenticated
  useEffect(() => {
    if (authLoading || !user) {
      setIsLoading(false);
      return;
    }
    if (loadedRef.current) return;
    loadedRef.current = true;
    loadProducts();
  }, [user, authLoading, loadProducts]);

  // Reset when user changes (logout/login)
  useEffect(() => {
    if (!user) {
      setProducts([]);
      setActiveProduct(null);
      setActiveProductId(null);
      setIsLoading(false);
      loadedRef.current = false;
    }
  }, [user]);

  const selectProduct = useCallback((product: Product) => {
    setActiveProduct(product);
    setActiveProductId(product.id);
    setShowSelector(false);
  }, []);

  const openSelector = useCallback(() => {
    setShowSelector(true);
  }, []);

  const closeSelector = useCallback(() => {
    // Only close if a product is already selected
    if (activeProduct) {
      setShowSelector(false);
    }
  }, [activeProduct]);

  const refreshProducts = useCallback(async () => {
    setIsLoading(true);
    loadedRef.current = false;
    try {
      const list = await listProducts();
      const active = list.filter((p) => p.is_active);
      setProducts(active);
      // If current product was archived, reset
      if (activeProduct && !active.find((p) => p.id === activeProduct.id)) {
        if (active.length === 1) {
          setActiveProduct(active[0]);
          setActiveProductId(active[0].id);
        } else {
          setActiveProduct(null);
          setActiveProductId(null);
          if (active.length > 1) setShowSelector(true);
        }
      }
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
      loadedRef.current = true;
    }
  }, [activeProduct]);

  return (
    <ProductContext.Provider
      value={{
        products,
        activeProduct,
        isLoading,
        showSelector,
        selectProduct,
        openSelector,
        closeSelector,
        refreshProducts,
      }}
    >
      {children}
    </ProductContext.Provider>
  );
}

export function useProduct(): ProductContextValue {
  const ctx = useContext(ProductContext);
  if (!ctx) throw new Error("useProduct must be used within ProductProvider");
  return ctx;
}
