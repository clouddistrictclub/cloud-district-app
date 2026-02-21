import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Image, Alert, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useCartStore } from '../store/cartStore';
import { Ionicons } from '@expo/vector-icons';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

const resolveImageUri = (image: string | undefined | null) => {
  if (!image) return '';
  if (image.startsWith('/')) return `${API_URL}${image}`;
  return image;
};

export default function Cart() {
  const router = useRouter();
  const { items, updateQuantity, removeItem, getTotal, getSubtotal, getDiscount, getBulkDiscountActive, clearCart } = useCartStore();
  const subtotal = getSubtotal();
  const discount = getDiscount();
  const total = getTotal();
  const bulkActive = getBulkDiscountActive();
  const itemCount = items.reduce((sum, i) => sum + i.quantity, 0);

  const handleCheckout = () => {
    if (items.length === 0) {
      Alert.alert('Cart Empty', 'Please add items to your cart first');
      return;
    }
    router.push('/checkout');
  };

  const handleRemoveItem = (productId: string, productName: string) => {
    Alert.alert(
      'Remove Item',
      `Remove ${productName} from cart?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Remove', style: 'destructive', onPress: () => removeItem(productId) }
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Cart</Text>
        {items.length > 0 && (
          <TouchableOpacity onPress={() => {
            Alert.alert(
              'Clear Cart',
              'Remove all items from cart?',
              [
                { text: 'Cancel', style: 'cancel' },
                { text: 'Clear', style: 'destructive', onPress: clearCart }
              ]
            );
          }}>
            <Text style={styles.clearText}>Clear</Text>
          </TouchableOpacity>
        )}
      </View>

      {items.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Ionicons name="cart-outline" size={80} color="#333" />
          <Text style={styles.emptyText}>Your cart is empty</Text>
          <TouchableOpacity style={styles.shopButton} onPress={() => router.push('/(tabs)/shop')}>
            <Text style={styles.shopButtonText}>Start Shopping</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <>
          <ScrollView style={styles.content}>
            {items.map((item) => (
              <View key={item.productId} style={styles.cartItem}>
                {item.image ? (
                  Platform.OS === 'web' ? (
                    <img
                      src={resolveImageUri(item.image)}
                      style={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 8 }}
                      alt={item.name}
                    />
                  ) : (
                    <Image source={{ uri: resolveImageUri(item.image) }} style={styles.itemImage} />
                  )
                ) : null}
                <View style={styles.itemInfo}>
                  <Text style={styles.itemName} numberOfLines={2}>{item.name}</Text>
                  <Text style={styles.itemPrice}>${item.price.toFixed(2)}</Text>
                  
                  <View style={styles.quantityContainer}>
                    <TouchableOpacity 
                      style={styles.quantityButton}
                      onPress={() => updateQuantity(item.productId, item.quantity - 1)}
                    >
                      <Ionicons name="remove" size={16} color="#fff" />
                    </TouchableOpacity>
                    <Text style={styles.quantityText}>{item.quantity}</Text>
                    <TouchableOpacity 
                      style={styles.quantityButton}
                      onPress={() => updateQuantity(item.productId, item.quantity + 1)}
                    >
                      <Ionicons name="add" size={16} color="#fff" />
                    </TouchableOpacity>
                  </View>
                </View>
                <TouchableOpacity 
                  style={styles.removeButton}
                  onPress={() => handleRemoveItem(item.productId, item.name)}
                >
                  <Ionicons name="trash" size={20} color="#2E6BFF" />
                </TouchableOpacity>
              </View>
            ))}

            <View style={styles.summaryCard}>
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Subtotal ({itemCount} items)</Text>
                <Text style={styles.summaryValue}>${subtotal.toFixed(2)}</Text>
              </View>
              {bulkActive && (
                <View style={styles.summaryRow}>
                  <View style={styles.discountRow}>
                    <Ionicons name="pricetag" size={14} color="#22c55e" />
                    <Text style={styles.discountLabel}>Bulk Discount (10%)</Text>
                  </View>
                  <Text style={styles.discountValue}>-${discount.toFixed(2)}</Text>
                </View>
              )}
              {!bulkActive && itemCount > 0 && (
                <View style={styles.discountHint}>
                  <Ionicons name="information-circle-outline" size={14} color="#666" />
                  <Text style={styles.discountHintText}>Add {10 - itemCount} more item{10 - itemCount !== 1 ? 's' : ''} for 10% off!</Text>
                </View>
              )}
              <View style={styles.summaryRow}>
                <Text style={styles.summaryNote}>Local Pickup Only</Text>
                <Text style={styles.summaryNote}>FREE</Text>
              </View>
            </View>
          </ScrollView>

          <View style={styles.footer}>
            <View style={styles.totalContainer}>
              <Text style={styles.totalLabel}>Total</Text>
              <Text style={styles.totalAmount}>${total.toFixed(2)}</Text>
            </View>
            <TouchableOpacity style={styles.checkoutButton} onPress={handleCheckout}>
              <Text style={styles.checkoutButtonText}>Proceed to Checkout</Text>
              <Ionicons name="arrow-forward" size={20} color="#fff" />
            </TouchableOpacity>
          </View>
        </>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0c0c0c',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
  },
  backButton: {
    width: 40,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  clearText: {
    fontSize: 14,
    color: '#2E6BFF',
    fontWeight: '600',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
  },
  emptyText: {
    fontSize: 18,
    color: '#A0A0A0',
    marginTop: 16,
    marginBottom: 32,
  },
  shopButton: {
    backgroundColor: '#2E6BFF',
    paddingHorizontal: 32,
    paddingVertical: 16,
    borderRadius: 18,
  },
  shopButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  cartItem: {
    flexDirection: 'row',
    backgroundColor: '#151515',
    borderRadius: 18,
    padding: 12,
    marginBottom: 12,
    gap: 12,
  },
  itemImage: {
    width: 80,
    height: 80,
    borderRadius: 18,
    backgroundColor: '#2a2a2a',
  },
  itemInfo: {
    flex: 1,
    justifyContent: 'space-between',
  },
  itemName: {
    fontSize: 14,
    color: '#fff',
    fontWeight: '600',
  },
  itemPrice: {
    fontSize: 16,
    color: '#2E6BFF',
    fontWeight: 'bold',
  },
  quantityContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  quantityButton: {
    width: 28,
    height: 28,
    backgroundColor: '#333',
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  quantityText: {
    fontSize: 16,
    color: '#fff',
    fontWeight: '600',
    minWidth: 20,
    textAlign: 'center',
  },
  removeButton: {
    padding: 8,
  },
  summaryCard: {
    backgroundColor: '#151515',
    borderRadius: 18,
    padding: 16,
    marginTop: 16,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  summaryLabel: {
    fontSize: 16,
    color: '#fff',
  },
  summaryValue: {
    fontSize: 16,
    color: '#fff',
    fontWeight: '600',
  },
  summaryNote: {
    fontSize: 14,
    color: '#666',
  },
  footer: {
    padding: 16,
    backgroundColor: '#151515',
    borderTopWidth: 1,
    borderTopColor: '#333',
  },
  totalContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  totalLabel: {
    fontSize: 18,
    color: '#fff',
    fontWeight: '600',
  },
  totalAmount: {
    fontSize: 24,
    color: '#fff',
    fontWeight: 'bold',
  },
  checkoutButton: {
    flexDirection: 'row',
    backgroundColor: '#2E6BFF',
    padding: 16,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  checkoutButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});