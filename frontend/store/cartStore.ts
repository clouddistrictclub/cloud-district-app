import { create } from 'zustand';
import { Platform } from 'react-native';

const BULK_DISCOUNT_THRESHOLD = 10;
const BULK_DISCOUNT_RATE = 0.10;
const STORAGE_KEY = 'cloud-district-cart';

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
  hydrateCart: () => void;
}

// --- Storage helpers (never called at module-load time) ---

function readCart(): CartItem[] {
  if (Platform.OS === 'web') {
    if (typeof window === 'undefined') return [];
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
      return [];
    } catch {
      return [];
    }
  }
  // Native: will be handled async
  return [];
}

function writeCart(items: CartItem[]) {
  if (Platform.OS === 'web') {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch {}
    return;
  }
  // Native: async write
  try {
    const AsyncStorage = require('@react-native-async-storage/async-storage').default;
    AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {}
}

function clearStorage() {
  if (Platform.OS === 'web') {
    if (typeof window === 'undefined') return;
    try { window.localStorage.removeItem(STORAGE_KEY); } catch {}
    return;
  }
  try {
    const AsyncStorage = require('@react-native-async-storage/async-storage').default;
    AsyncStorage.removeItem(STORAGE_KEY);
  } catch {}
}

export const useCartStore = create<CartStore>()((set, get) => ({
  items: [],
  _hydrated: false,

  hydrateCart: () => {
    if (Platform.OS === 'web') {
      const items = readCart();
      set({ items, _hydrated: true });
    } else {
      // Native: async read
      try {
        const AsyncStorage = require('@react-native-async-storage/async-storage').default;
        AsyncStorage.getItem(STORAGE_KEY).then((raw: string | null) => {
          if (raw) {
            try {
              const parsed = JSON.parse(raw);
              if (Array.isArray(parsed)) {
                set({ items: parsed, _hydrated: true });
                return;
              }
            } catch {}
          }
          set({ _hydrated: true });
        });
      } catch {
        set({ _hydrated: true });
      }
    }
  },

  addItem: (item) => {
    set((state) => {
      const items = state.items ?? [];
      const existing = items.find(i => i.productId === item.productId);
      let newItems: CartItem[];
      if (existing) {
        newItems = items.map(i =>
          i.productId === item.productId
            ? { ...i, quantity: i.quantity + 1 }
            : i
        );
      } else {
        newItems = [...items, { ...item, quantity: 1 }];
      }
      writeCart(newItems);
      return { items: newItems };
    });
  },

  removeItem: (productId) => {
    set((state) => {
      const newItems = (state.items ?? []).filter(i => i.productId !== productId);
      writeCart(newItems);
      return { items: newItems };
    });
  },

  updateQuantity: (productId, quantity) => {
    if (quantity <= 0) {
      get().removeItem(productId);
      return;
    }
    set((state) => {
      const newItems = (state.items ?? []).map(i =>
        i.productId === productId ? { ...i, quantity } : i
      );
      writeCart(newItems);
      return { items: newItems };
    });
  },

  clearCart: () => {
    clearStorage();
    set({ items: [] });
  },

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
}));
