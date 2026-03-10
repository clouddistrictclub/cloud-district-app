import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useCartStore } from '../store/cartStore';
import { useAuthStore } from '../store/authStore';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../theme';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface ActiveReward {
  id: string;
  tierId: string;
  tierName: string;
  rewardAmount: number;
  pointsSpent: number;
}

const paymentMethods = [
  { id: 'cash_on_pickup', name: 'Cash on Pickup', fee: 0, icon: 'wallet' },
  { id: 'zelle', name: 'Zelle', fee: 0, icon: 'flash' },
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
  const { user, refreshUser, token } = useAuthStore();
  const [selectedPickupTime, setSelectedPickupTime] = useState<string>('');
  const [selectedPayment, setSelectedPayment] = useState<string>('');
  const [selectedReward, setSelectedReward] = useState<ActiveReward | null>(null);
  const [activeRewards, setActiveRewards] = useState<ActiveReward[]>([]);
  const [coupon, setCoupon] = useState<{ amount: number; expiresAt: string } | null>(null);
  const [couponApplied, setCouponApplied] = useState(false);
  const [storeCreditApplied, setStoreCreditApplied] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingRewards, setLoadingRewards] = useState(true);

  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  useEffect(() => {
    loadActiveRewards();
    loadCoupon();
  }, []);

  const loadCoupon = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/me/coupon`, { headers: { Authorization: `Bearer ${token}` } });
      setCoupon(res.data.coupon);
    } catch (e) {
      // silent
    }
  };

  const loadActiveRewards = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/loyalty/rewards`, { headers: { Authorization: `Bearer ${token}` } });
      setActiveRewards(res.data);
    } catch (error) {
      console.error('Failed to load rewards:', error);
    } finally {
      setLoadingRewards(false);
    }
  };

  const subtotal = getTotal();
  const selectedMethod = paymentMethods.find(m => m.id === selectedPayment);
  const convenienceFee = selectedMethod ? subtotal * selectedMethod.fee : 0;
  const rewardDiscount = selectedReward ? Math.min(selectedReward.rewardAmount, subtotal + convenienceFee) : 0;
  const couponDiscount = coupon && couponApplied ? Math.min(coupon.amount, subtotal + convenienceFee - rewardDiscount) : 0;
  const availableCredit = user?.creditBalance || 0;
  const preTotalBeforeCredit = Math.max(0, subtotal + convenienceFee - rewardDiscount - couponDiscount);
  const creditDiscount = storeCreditApplied ? Math.min(availableCredit, preTotalBeforeCredit) : 0;
  const total = Math.max(0, preTotalBeforeCredit - creditDiscount);

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
        rewardId: selectedReward?.id || null,
        couponApplied: coupon && couponApplied ? true : false,
        storeCreditApplied: parseFloat(creditDiscount.toFixed(2)),
      };

      const response = await axios.post(`${API_URL}/api/orders`, orderData, authHeaders);
      const orderId = response.data.id;

      clearCart();
      await refreshUser();

      if (selectedPayment === 'cash_on_pickup') {
        router.replace(`/order-confirmation?orderId=${orderId}&status=${encodeURIComponent(response.data.status)}&paymentMethod=${encodeURIComponent(selectedMethod?.name || '')}&total=${total.toFixed(2)}&pickupTime=${encodeURIComponent(selectedPickupTime)}`);
      } else {
        router.replace(`/payment-instructions?orderId=${orderId}&method=${selectedPayment}&amount=${total.toFixed(2)}`);
      }
    } catch (error: any) {
      console.error('Failed to place order:', error);
      Alert.alert('Order Failed', error.response?.data?.detail || 'Failed to place order');
    } finally {
      setLoading(false);
    }
  };

  const toggleReward = (reward: ActiveReward) => {
    if (selectedReward?.id === reward.id) {
      setSelectedReward(null);
    } else {
      setSelectedReward(reward);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton} data-testid="checkout-back-btn">
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Checkout</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView style={styles.content}>
        {/* Pickup Time */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Pickup Time</Text>
          <Text style={styles.sectionSubtitle}>Local Pickup Only</Text>
          {pickupTimes.map((time) => (
            <TouchableOpacity
              key={time}
              style={[styles.optionCard, selectedPickupTime === time && styles.optionCardSelected]}
              onPress={() => setSelectedPickupTime(time)}
              data-testid={`pickup-time-${time.substring(0, 5)}`}
            >
              <View style={styles.radioOuter}>
                {selectedPickupTime === time && <View style={styles.radioInner} />}
              </View>
              <Text style={styles.optionText}>{time}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Payment Method */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Payment Method</Text>
          <Text style={styles.sectionSubtitle}>Manual confirmation required</Text>
          {paymentMethods.map((method) => (
            <TouchableOpacity
              key={method.id}
              style={[styles.optionCard, selectedPayment === method.id && styles.optionCardSelected]}
              onPress={() => setSelectedPayment(method.id)}
              data-testid={`payment-method-${method.id}`}
            >
              <View style={styles.radioOuter}>
                {selectedPayment === method.id && <View style={styles.radioInner} />}
              </View>
              <Ionicons name={method.icon as any} size={20} color={theme.colors.primary} />
              <Text style={styles.optionText}>{method.name}</Text>
              {method.fee > 0 && (
                <Text style={styles.feeText}>+{(method.fee * 100).toFixed(0)}% fee</Text>
              )}
            </TouchableOpacity>
          ))}
        </View>

        {/* Cloudz Tier Rewards */}
        {!loadingRewards && activeRewards.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Apply Cloudz Reward</Text>
            <Text style={styles.sectionSubtitle}>Select a reward to apply</Text>
            {activeRewards.map((reward) => (
              <TouchableOpacity
                key={reward.id}
                style={[
                  styles.rewardCard,
                  selectedReward?.id === reward.id && styles.rewardCardSelected,
                ]}
                onPress={() => toggleReward(reward)}
                data-testid={`checkout-reward-${reward.tierId}`}
              >
                <View style={[styles.radioOuter, { borderColor: '#fbbf24' }]}>
                  {selectedReward?.id === reward.id && <View style={[styles.radioInner, { backgroundColor: '#fbbf24' }]} />}
                </View>
                <Ionicons name="star" size={20} color="#fbbf24" />
                <View style={{ flex: 1 }}>
                  <Text style={styles.rewardName}>{reward.tierName}</Text>
                  <Text style={styles.rewardDetail}>{reward.pointsSpent.toLocaleString()} points redeemed</Text>
                </View>
                <Text style={styles.rewardAmount}>-${reward.rewardAmount.toFixed(2)}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {!loadingRewards && activeRewards.length === 0 && (user?.loyaltyPoints || 0) > 0 && (
          <View style={styles.section}>
            <TouchableOpacity
              style={styles.earnRewardsCard}
              onPress={() => router.push('/cloudz')}
              data-testid="go-to-cloudz-btn"
            >
              <Ionicons name="star" size={24} color="#fbbf24" />
              <View style={{ flex: 1 }}>
                <Text style={styles.earnRewardsTitle}>You have {(user?.loyaltyPoints || 0).toLocaleString()} Cloudz Points</Text>
                <Text style={styles.earnRewardsSubtitle}>Redeem points for tier rewards</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#666" />
            </TouchableOpacity>
          </View>
        )}

        {/* Store Credit */}
        {availableCredit > 0 && (
          <View style={styles.section}>
            <TouchableOpacity
              style={[styles.optionCard, storeCreditApplied && styles.optionCardSelected, { borderColor: '#38bdf8', backgroundColor: storeCreditApplied ? '#0c1d2a' : '#111' }]}
              onPress={() => setStoreCreditApplied(!storeCreditApplied)}
              data-testid="store-credit-toggle"
            >
              <View style={[styles.radioOuter, { borderColor: '#38bdf8' }]}>
                {storeCreditApplied && <View style={[styles.radioInner, { backgroundColor: '#38bdf8' }]} />}
              </View>
              <Ionicons name="card-outline" size={20} color="#38bdf8" />
              <View style={{ flex: 1 }}>
                <Text style={[styles.optionText, { color: '#38bdf8' }]}>Apply Store Credit</Text>
                <Text style={[styles.rewardDetail, { color: '#7dd3fc' }]}>
                  ${availableCredit.toFixed(2)} available
                </Text>
              </View>
              <Text style={[styles.rewardAmount, { color: '#38bdf8' }]}>
                -{storeCreditApplied ? `$${Math.min(availableCredit, preTotalBeforeCredit).toFixed(2)}` : `$${availableCredit.toFixed(2)}`}
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Next Order Coupon */}
        {coupon && (
          <View style={styles.section}>
            <TouchableOpacity
              style={[styles.optionCard, couponApplied && styles.optionCardSelected, { borderColor: '#10b981', backgroundColor: couponApplied ? '#0d1f18' : '#111' }]}
              onPress={() => setCouponApplied(!couponApplied)}
              data-testid="coupon-toggle"
            >
              <View style={[styles.radioOuter, { borderColor: '#10b981' }]}>
                {couponApplied && <View style={[styles.radioInner, { backgroundColor: '#10b981' }]} />}
              </View>
              <Ionicons name="gift-outline" size={20} color="#10b981" />
              <View style={{ flex: 1 }}>
                <Text style={[styles.optionText, { color: '#10b981' }]}>Apply ${coupon.amount.toFixed(2)} Welcome-Back Coupon</Text>
                <Text style={[styles.rewardDetail, { color: '#4ade80' }]}>
                  Expires {new Date(coupon.expiresAt).toLocaleDateString()}
                </Text>
              </View>
              <Text style={[styles.rewardAmount, { color: '#10b981' }]}>-${coupon.amount.toFixed(2)}</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Order Summary */}
        <View style={styles.summaryCard} data-testid="order-summary">
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
          {selectedReward && (
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>{selectedReward.tierName} Reward</Text>
              <Text style={[styles.summaryValue, { color: theme.colors.success }]}>-${rewardDiscount.toFixed(2)}</Text>
            </View>
          )}
          {couponApplied && coupon && (
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Coupon Discount</Text>
              <Text style={[styles.summaryValue, { color: '#10b981' }]}>-${couponDiscount.toFixed(2)}</Text>
            </View>
          )}
          {storeCreditApplied && creditDiscount > 0 && (
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Store Credit</Text>
              <Text style={[styles.summaryValue, { color: '#38bdf8' }]}>-${creditDiscount.toFixed(2)}</Text>
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
          data-testid="place-order-btn"
        >
          {loading ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.placeOrderText}>Place Order - ${total.toFixed(2)}</Text>
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
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
    backgroundColor: theme.colors.card,
    padding: 16,
    borderRadius: theme.borderRadius.lg,
    marginBottom: 8,
    borderWidth: 2,
    borderColor: 'transparent',
    gap: 12,
  },
  optionCardSelected: {
    borderColor: theme.colors.primary,
    backgroundColor: '#1e1e2e',
  },
  radioOuter: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: theme.colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: theme.colors.primary,
  },
  optionText: {
    flex: 1,
    fontSize: 14,
    color: '#fff',
  },
  feeText: {
    fontSize: 12,
    color: theme.colors.warning,
  },
  rewardCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.card,
    padding: 16,
    borderRadius: theme.borderRadius.lg,
    marginBottom: 8,
    borderWidth: 2,
    borderColor: 'transparent',
    gap: 12,
  },
  rewardCardSelected: {
    borderColor: '#fbbf24',
    backgroundColor: '#1a1810',
  },
  rewardName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  rewardDetail: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  rewardAmount: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.colors.success,
  },
  earnRewardsCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.card,
    padding: 16,
    borderRadius: theme.borderRadius.lg,
    gap: 12,
  },
  earnRewardsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fbbf24',
  },
  earnRewardsSubtitle: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  summaryCard: {
    backgroundColor: theme.colors.card,
    padding: 16,
    borderRadius: theme.borderRadius.lg,
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
    color: theme.colors.textMuted,
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
    backgroundColor: theme.colors.card,
    borderTopWidth: 1,
    borderTopColor: '#333',
  },
  placeOrderButton: {
    backgroundColor: theme.colors.primary,
    padding: 16,
    borderRadius: theme.borderRadius.lg,
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
