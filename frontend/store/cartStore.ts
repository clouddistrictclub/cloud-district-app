import { create } from 'zustand';

interface CartItem {
  productId: string;
  quantity: number;
  name: string;
  price: number;
  image: string;
}

interface CartState {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  clearCart: () => void;
  getTotal: () => number;
  getItemCount: () => number;
  getSubtotal: () => number;
  getDiscount: () => number;
  getBulkDiscountActive: () => boolean;
}

const BULK_DISCOUNT_THRESHOLD = 10;
const BULK_DISCOUNT_RATE = 0.10;

export const useCartStore = create<CartState>((set, get) => ({
  items: [],

  addItem: (item: CartItem) => {
    const items = get().items;
    const existingItem = items.find(i => i.productId === item.productId);
    
    if (existingItem) {
      set({
        items: items.map(i => 
          i.productId === item.productId 
            ? { ...i, quantity: i.quantity + item.quantity }
            : i
        )
      });
    } else {
      set({ items: [...items, item] });
    }
  },

  removeItem: (productId: string) => {
    set({ items: get().items.filter(i => i.productId !== productId) });
  },

  updateQuantity: (productId: string, quantity: number) => {
    if (quantity <= 0) {
      get().removeItem(productId);
    } else {
      set({
        items: get().items.map(i => 
          i.productId === productId ? { ...i, quantity } : i
        )
      });
    }
  },

  clearCart: () => set({ items: [] }),

  getSubtotal: () => {
    return get().items.reduce((total, item) => total + (item.price * item.quantity), 0);
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
    return get().items.reduce((count, item) => count + item.quantity, 0);
  }
}));