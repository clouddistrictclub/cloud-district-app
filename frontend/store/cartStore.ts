import { create } from 'zustand';
import { persist, createJSONStorage, StateStorage } from 'zustand/middleware';
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

// Custom storage that works for both web and native
const createCustomStorage = (): StateStorage => {
  const isWeb = Platform.OS === 'web';
  
  return {
    getItem: async (name: string): Promise<string | null> => {
      if (isWeb) {
        if (typeof window !== 'undefined') {
          const value = window.localStorage.getItem(name);
          return value;
        }
        return null;
      }
      // Native - use AsyncStorage
      return AsyncStorage.getItem(name);
    },
    setItem: async (name: string, value: string): Promise<void> => {
      if (isWeb) {
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(name, value);
        }
        return;
      }
      // Native - use AsyncStorage
      return AsyncStorage.setItem(name, value);
    },
    removeItem: async (name: string): Promise<void> => {
      if (isWeb) {
        if (typeof window !== 'undefined') {
          window.localStorage.removeItem(name);
        }
        return;
      }
      // Native - use AsyncStorage
      return AsyncStorage.removeItem(name);
    },
  };
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
      storage: createJSONStorage(() => customStorage),
      skipHydration: false,
      merge: (persisted, current) => ({
        ...current,
        ...(persisted as Partial<CartStore>),
        items: Array.isArray((persisted as any)?.items) ? (persisted as any).items : [],
      }),
    }
  )
);
