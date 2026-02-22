import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const BULK_DISCOUNT_THRESHOLD = 10;
const BULK_DISCOUNT_RATE = 0.10;

interface CartItem {
  productId: string;
  name: string;
  price: number;
  image: string;
  quantity: number;
}

interface CartStore {
  items: CartItem[];
  addItem: (item: Omit<CartItem, 'quantity'>) => void;
  removeItem: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  clearCart: () => void;
  getSubtotal: () => number;
  getBulkDiscountActive: () => boolean;
  getDiscount: () => number;
  getTotal: () => number;
  getItemCount: () => number;
}

// In-memory fallback when localStorage is unavailable
const memoryStore = new Map<string, string>();
const fallbackStorage = {
  getItem: (name: string) => memoryStore.get(name) ?? null,
  setItem: (name: string, value: string) => { memoryStore.set(name, value); },
  removeItem: (name: string) => { memoryStore.delete(name); },
};

// Custom storage adapter for Zustand persist
const customStorage = {
  getItem: (name: string): string | null => {
    if (Platform.OS !== 'web') {
      // For native, use AsyncStorage (returns Promise, but Zustand handles this)
      return null; // AsyncStorage handled separately
    }
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
      try {
        return window.localStorage.getItem(name);
      } catch {
        return memoryStore.get(name) ?? null;
      }
    }
    return memoryStore.get(name) ?? null;
  },
  setItem: (name: string, value: string): void => {
    if (Platform.OS !== 'web') {
      return; // AsyncStorage handled separately
    }
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
      try {
        window.localStorage.setItem(name, value);
      } catch {
        memoryStore.set(name, value);
      }
    } else {
      memoryStore.set(name, value);
    }
  },
  removeItem: (name: string): void => {
    if (Platform.OS !== 'web') {
      return;
    }
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
      try {
        window.localStorage.removeItem(name);
      } catch {
        memoryStore.delete(name);
      }
    } else {
      memoryStore.delete(name);
    }
  },
};

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],

      addItem: (item) => {
        set((state) => {
          const items = state.items ?? [];
          const existing = items.find(i => i.productId === item.productId);
          if (existing) {
            return {
              items: items.map(i =>
                i.productId === item.productId
                  ? { ...i, quantity: i.quantity + 1 }
                  : i
              ),
            };
          }
          return { items: [...items, { ...item, quantity: 1 }] };
        });
      },

      removeItem: (productId) => {
        set((state) => ({
          items: (state.items ?? []).filter(i => i.productId !== productId),
        }));
      },

      updateQuantity: (productId, quantity) => {
        if (quantity <= 0) {
          get().removeItem(productId);
          return;
        }
        set((state) => ({
          items: (state.items ?? []).map(i =>
            i.productId === productId ? { ...i, quantity } : i
          ),
        }));
      },

      clearCart: () => set({ items: [] }),

      getSubtotal: () => {
        return (get().items ?? []).reduce((sum, item) => sum + item.price * item.quantity, 0);
      },

      getBulkDiscountActive: () => {
        return get().getItemCount() >= BULK_DISCOUNT_THRESHOLD;
      },

      getDiscount: () => {
        if (!get().getBulkDiscountActive()) return 0;
        return Math.round(get().getSubtotal() * BULK_DISCOUNT_RATE * 100) / 100;
      },

      getTotal: () => {
        return Math.round((get().getSubtotal() - get().getDiscount()) * 100) / 100;
      },

      getItemCount: () => {
        return (get().items ?? []).reduce((count, item) => count + item.quantity, 0);
      },
    }),
    {
      name: 'cloud-district-cart',
      storage: createJSONStorage(getStorage),
      merge: (persisted, current) => ({
        ...current,
        ...(persisted as Partial<CartStore>),
        items: Array.isArray((persisted as any)?.items) ? (persisted as any).items : [],
      }),
    }
  )
);
