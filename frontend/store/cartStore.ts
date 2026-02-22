import { create } from 'zustand';
import { persist, createJSONStorage, StateStorage } from 'zustand/middleware';
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

// Create a proper web storage that checks for browser environment
const webStorage: StateStorage = {
  getItem: (name: string): string | null => {
    if (typeof window === 'undefined') return null;
    return window.localStorage.getItem(name);
  },
  setItem: (name: string, value: string): void => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(name, value);
  },
  removeItem: (name: string): void => {
    if (typeof window === 'undefined') return;
    window.localStorage.removeItem(name);
  },
};

// For native, we need AsyncStorage
const getStorage = () => {
  if (Platform.OS === 'web') {
    return createJSONStorage(() => webStorage);
  }
  // Native platforms
  try {
    const AsyncStorage = require('@react-native-async-storage/async-storage').default;
    return createJSONStorage(() => AsyncStorage);
  } catch {
    return createJSONStorage(() => webStorage);
  }
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
      storage: getStorage(),
      skipHydration: true,
      partialize: (state) => ({ items: state.items }),
    }
  )
);
