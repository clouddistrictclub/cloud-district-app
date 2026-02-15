import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { useState } from 'react';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useCartStore } from '../store/cartStore';
import { useAuthStore } from '../store/authStore';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

const paymentMethods = [
  { id: 'zelle', name: 'Zelle', fee: 0, icon: 'flash' },
  { id: 'venmo', name: 'Venmo', fee: 0.03, icon: 'logo-venmo' },
  { id: 'cashapp', name: 'Cash App', fee: 0.03, icon: 'cash' },
  { id: 'chime', name: 'Chime', fee: 0.03, icon: 'card' },
];

const pickupTimes = [
  'Today - 12:00 PM - 2:00 PM',
  'Today - 2:00 PM - 4:00 PM',
  'Today - 4:00 PM - 6:00 PM',
  'Tomorrow - 10:00 AM - 12:00 PM',
  'Tomorrow - 12:00 PM - 2:00 PM',
  'Tomorrow - 2:00 PM - 4:00 PM',
];

export default function Checkout() {
  const router = useRouter();
  const { items, getTotal, clearCart } = useCartStore();
  const { user, refreshUser } = useAuthStore();
  const [selectedPickupTime, setSelectedPickupTime] = useState<string>('');
  const [selectedPayment, setSelectedPayment] = useState<string>('');
  const [loyaltyPointsToUse, setLoyaltyPointsToUse] = useState(0);
  const [loading, setLoading] = useState(false);

  const subtotal = getTotal();
  const selectedMethod = paymentMethods.find(m => m.id === selectedPayment);
  const convenienceFee = selectedMethod ? subtotal * selectedMethod.fee : 0;
  const loyaltyDiscount = loyaltyPointsToUse * 0.1; // $0.10 per point
  const total = subtotal + convenienceFee - loyaltyDiscount;

  const handlePlaceOrder = async () => {
    if (!selectedPickupTime) {
      Alert.alert('Pickup Time Required', 'Please select a pickup time');
      return;
    }

    if (!selectedPayment) {
      Alert.alert('Payment Method Required', 'Please select a payment method');
      return;
    }

    setLoading(true);
    try {
      const orderData = {
        items: items.map(item => ({
          productId: item.productId,
          quantity: item.quantity,
          name: item.name,
          price: item.price,
        })),
        total: parseFloat(total.toFixed(2)),
        pickupTime: selectedPickupTime,
        paymentMethod: selectedMethod?.name || '',
        loyaltyPointsUsed: loyaltyPointsToUse,
      };

      const response = await axios.post(`${API_URL}/api/orders`, orderData);
      const orderId = response.data.id;

      clearCart();
      await refreshUser();

      // Navigate to payment instructions
      router.replace(`/payment-instructions?orderId=${orderId}&method=${selectedPayment}&amount=${total.toFixed(2)}`);
    } catch (error: any) {
      console.error('Failed to place order:', error);
      Alert.alert('Order Failed', error.response?.data?.detail || 'Failed to place order');
    } finally {
      setLoading(false);
    }
  };

  const maxLoyaltyPoints = Math.min(
    user?.loyaltyPoints || 0,
    Math.floor(subtotal * 10) // Max 100% discount
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Checkout</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView style={styles.content}>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Pickup Time</Text>
          <Text style={styles.sectionSubtitle}>Local Pickup Only</Text>
          {pickupTimes.map((time) => (
            <TouchableOpacity
              key={time}
              style={[
                styles.optionCard,
                selectedPickupTime === time && styles.optionCardSelected
              ]}
              onPress={() => setSelectedPickupTime(time)}
            >
              <View style={styles.radioOuter}>
                {selectedPickupTime === time && <View style={styles.radioInner} />}
              </View>
              <Text style={styles.optionText}>{time}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Payment Method</Text>
          <Text style={styles.sectionSubtitle}>Manual confirmation required</Text>
          {paymentMethods.map((method) => (
            <TouchableOpacity
              key={method.id}
              style={[
                styles.optionCard,
                selectedPayment === method.id && styles.optionCardSelected
              ]}
              onPress={() => setSelectedPayment(method.id)}
            >
              <View style={styles.radioOuter}>
                {selectedPayment === method.id && <View style={styles.radioInner} />}
              </View>
              <Ionicons name={method.icon as any} size={20} color="#2E6BFF" />
              <Text style={styles.optionText}>{method.name}</Text>
              {method.fee > 0 && (
                <Text style={styles.feeText}>+{(method.fee * 100).toFixed(0)}% fee</Text>
              )}
            </TouchableOpacity>
          ))}
        </View>

        {(user?.loyaltyPoints || 0) > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Cloudz Points</Text>
            <Text style={styles.sectionSubtitle}>You have {user?.loyaltyPoints} points available</Text>
            <View style={styles.loyaltyCard}>
              <View style={styles.loyaltyInfo}>
                <Ionicons name="star" size={24} color="#fbbf24" />
                <View style={{ flex: 1 }}>
                  <Text style={styles.loyaltyText}>Use Points</Text>
                  <Text style={styles.loyaltySubtext}>$0.10 per point</Text>
                </View>
                <View style={styles.pointsSelector}>
                  <TouchableOpacity 
                    style={styles.pointsButton}
                    onPress={() => setLoyaltyPointsToUse(Math.max(0, loyaltyPointsToUse - 10))}
                  >
                    <Ionicons name="remove" size={16} color="#fff" />
                  </TouchableOpacity>
                  <Text style={styles.pointsText}>{loyaltyPointsToUse}</Text>
                  <TouchableOpacity 
                    style={styles.pointsButton}
                    onPress={() => setLoyaltyPointsToUse(Math.min(maxLoyaltyPoints, loyaltyPointsToUse + 10))}
                  >
                    <Ionicons name="add" size={16} color="#fff" />
                  </TouchableOpacity>
                </View>
              </View>
              {loyaltyPointsToUse > 0 && (
                <Text style={styles.discountText}>-${loyaltyDiscount.toFixed(2)} discount</Text>
              )}
            </View>
          </View>
        )}

        <View style={styles.summaryCard}>
          <Text style={styles.summaryTitle}>Order Summary</Text>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Subtotal</Text>
            <Text style={styles.summaryValue}>${subtotal.toFixed(2)}</Text>
          </View>
          {convenienceFee > 0 && (
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Convenience Fee</Text>
              <Text style={styles.summaryValue}>${convenienceFee.toFixed(2)}</Text>
            </View>
          )}
          {loyaltyPointsToUse > 0 && (
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Loyalty Discount</Text>
              <Text style={[styles.summaryValue, { color: '#10b981' }]}>-${loyaltyDiscount.toFixed(2)}</Text>
            </View>
          )}
          <View style={styles.divider} />
          <View style={styles.summaryRow}>
            <Text style={styles.totalLabel}>Total</Text>
            <Text style={styles.totalValue}>${total.toFixed(2)}</Text>
          </View>
          <Text style={styles.noteText}>
            You'll receive payment instructions after placing your order
          </Text>
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity 
          style={[styles.placeOrderButton, loading && styles.buttonDisabled]} 
          onPress={handlePlaceOrder}
          disabled={loading}
        >
          <Text style={styles.placeOrderText}>
            {loading ? 'Placing Order...' : `Place Order - $${total.toFixed(2)}`}
          </Text>
        </TouchableOpacity>
      </View>
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
  content: {
    flex: 1,
    padding: 16,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  sectionSubtitle: {
    fontSize: 14,
    color: '#666',
    marginBottom: 12,
  },
  optionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#151515',
    padding: 16,
    borderRadius: 18,
    marginBottom: 8,
    borderWidth: 2,
    borderColor: 'transparent',
    gap: 12,
  },
  optionCardSelected: {
    borderColor: '#2E6BFF',
    backgroundColor: '#1e1e2e',
  },
  radioOuter: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#2E6BFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#2E6BFF',
  },
  optionText: {
    flex: 1,
    fontSize: 14,
    color: '#fff',
  },
  feeText: {
    fontSize: 12,
    color: '#fbbf24',
  },
  loyaltyCard: {
    backgroundColor: '#151515',
    padding: 16,
    borderRadius: 18,
  },
  loyaltyInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 8,
  },
  loyaltyText: {
    fontSize: 16,
    color: '#fff',
    fontWeight: '600',
  },
  loyaltySubtext: {
    fontSize: 12,
    color: '#666',
  },
  pointsSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  pointsButton: {
    width: 28,
    height: 28,
    backgroundColor: '#333',
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pointsText: {
    fontSize: 16,
    color: '#fff',
    fontWeight: 'bold',
    minWidth: 40,
    textAlign: 'center',
  },
  discountText: {
    fontSize: 14,
    color: '#10b981',
    fontWeight: '600',
    textAlign: 'right',
  },
  summaryCard: {
    backgroundColor: '#151515',
    padding: 16,
    borderRadius: 18,
    marginBottom: 16,
  },
  summaryTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 16,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  summaryLabel: {
    fontSize: 14,
    color: '#A0A0A0',
  },
  summaryValue: {
    fontSize: 14,
    color: '#fff',
  },
  divider: {
    height: 1,
    backgroundColor: '#333',
    marginVertical: 12,
  },
  totalLabel: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  totalValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  noteText: {
    fontSize: 12,
    color: '#666',
    marginTop: 12,
    fontStyle: 'italic',
  },
  footer: {
    padding: 16,
    backgroundColor: '#151515',
    borderTopWidth: 1,
    borderTopColor: '#333',
  },
  placeOrderButton: {
    backgroundColor: '#2E6BFF',
    padding: 16,
    borderRadius: 18,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  placeOrderText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
