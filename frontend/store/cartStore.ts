import { create } from 'zustand';
import { persist, PersistStorage } from 'zustand/middleware';
import { Platform } from 'react-native';

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
  _hydrated: boolean;
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

// Custom PersistStorage that lazily checks for window/localStorage on EVERY call.
// This avoids the SSR trap where createJSONStorage caches the storage at module-load time.
const cartStorage: PersistStorage<CartStore> = {
  getItem: (name) => {
    if (Platform.OS !== 'web') {
      // Native: use AsyncStorage (dynamic import to avoid web bundling issues)
      try {
        const AsyncStorage = require('@react-native-async-storage/async-storage').default;
        return AsyncStorage.getItem(name).then((str: string | null) => {
          if (!str) return null;
          return JSON.parse(str);
        });
      } catch {
        return null;
      }
    }
    // Web: safely access localStorage
    if (typeof window === 'undefined') return null;
    try {
      const str = window.localStorage.getItem(name);
      if (!str) return null;
      return JSON.parse(str);
    } catch {
      return null;
    }
  },
  setItem: (name, value) => {
    if (Platform.OS !== 'web') {
      try {
        const AsyncStorage = require('@react-native-async-storage/async-storage').default;
        AsyncStorage.setItem(name, JSON.stringify(value));
      } catch {}
      return;
    }
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(name, JSON.stringify(value));
    } catch {}
  },
  removeItem: (name) => {
    if (Platform.OS !== 'web') {
      try {
        const AsyncStorage = require('@react-native-async-storage/async-storage').default;
        AsyncStorage.removeItem(name);
      } catch {}
      return;
    }
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.removeItem(name);
    } catch {}
  },
};

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],
      _hydrated: false,

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
      storage: cartStorage,
      skipHydration: true,
      merge: (persisted, current) => {
        // persisted comes from storage in format {state: {...}, version: N}
        // We need to extract items from persisted.state if it exists
        const persistedData = persisted as any;
        const persistedState = persistedData?.state || persistedData;
        const items = Array.isArray(persistedState?.items) ? persistedState.items : [];
        return {
          ...current,
          items,
          _hydrated: true,
        };
      },
    }
  )
);
