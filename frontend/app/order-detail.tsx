import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useState, useEffect } from 'react';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import { useAuthStore } from '../store/authStore';
import { crossAlert } from '../utils/crossAlert';
import { API_URL } from '../constants/api';

interface OrderDetail {
  id: string;
  items: { productId: string; quantity: number; name: string; price: number }[];
  total: number;
  pickupTime: string;
  paymentMethod: string;
  status: string;
  loyaltyPointsEarned: number;
  loyaltyPointsUsed: number;
  createdAt: string;
}

export default function OrderDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const { token } = useAuthStore();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id && token) loadOrder();
  }, [id, token]);

  const loadOrder = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/orders/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setOrder(res.data);
    } catch (e) {
      console.error('Failed to load order:', e);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Pending Payment': return '#fbbf24';
      case 'Paid': return '#3b82f6';
      case 'Ready for Pickup': return '#10b981';
      case 'Completed': return '#6b7280';
      case 'Cancelled': return '#ef4444';
      default: return '#999';
    }
  };

  const handleCancel = () => {
    crossAlert(
      'Cancel Order',
      'Are you sure you want to cancel this order? Inventory will be restored.',
      [
        { text: 'Keep Order', style: 'cancel' },
        {
          text: 'Cancel Order', style: 'destructive',
          onPress: async () => {
            try {
              await axios.post(
                `${API_URL}/api/orders/${id}/cancel`,
                {},
                { headers: { Authorization: `Bearer ${token}` } }
              );
              await loadOrder();
            } catch (e: any) {
              crossAlert('Error', e.response?.data?.detail || 'Failed to cancel order');
            }
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={s.container} edges={['top']}>
        <Text style={s.loadingText}>Loading...</Text>
      </SafeAreaView>
    );
  }

  if (!order) {
    return (
      <SafeAreaView style={s.container} edges={['top']}>
        <View style={s.header}>
          <TouchableOpacity onPress={() => router.back()} data-testid="order-detail-back-btn">
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={s.title}>Order Not Found</Text>
          <View style={{ width: 24 }} />
        </View>
      </SafeAreaView>
    );
  }

  const shortId = order.id.slice(-8).toUpperCase();

  return (
    <SafeAreaView style={s.container} edges={['top']}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} data-testid="order-detail-back-btn">
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={s.title}>Order #{shortId}</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView style={s.content}>
        <View style={[s.statusBanner, { backgroundColor: getStatusColor(order.status) + '18' }]}>
          <Text style={[s.statusLabel, { color: getStatusColor(order.status) }]}>{order.status}</Text>
        </View>

        <View style={s.card}>
          <Text style={s.sectionTitle}>Items</Text>
          {order.items.map((item, i) => (
            <View key={i} style={s.itemRow} data-testid={`order-item-${i}`}>
              <Text style={s.itemQty}>{item.quantity}x</Text>
              <Text style={s.itemName}>{item.name}</Text>
              <Text style={s.itemPrice}>${(item.price * item.quantity).toFixed(2)}</Text>
            </View>
          ))}
          <View style={s.divider} />
          <View style={s.itemRow}>
            <Text style={s.totalLabel}>Total</Text>
            <Text style={s.totalValue}>${order.total.toFixed(2)}</Text>
          </View>
        </View>

        <View style={s.card}>
          <Text style={s.sectionTitle}>Details</Text>
          <View style={s.detailRow}>
            <Ionicons name="card" size={16} color="#666" />
            <Text style={s.detailLabel}>Payment</Text>
            <Text style={s.detailValue}>{order.paymentMethod}</Text>
          </View>
          <View style={s.detailRow}>
            <Ionicons name="time" size={16} color="#666" />
            <Text style={s.detailLabel}>Pickup</Text>
            <Text style={s.detailValue}>{order.pickupTime}</Text>
          </View>
          <View style={s.detailRow}>
            <Ionicons name="calendar" size={16} color="#666" />
            <Text style={s.detailLabel}>Placed</Text>
            <Text style={s.detailValue}>
              {new Date(order.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            </Text>
          </View>
          {order.loyaltyPointsEarned > 0 && (
            <View style={s.detailRow}>
              <Ionicons name="star" size={16} color="#fbbf24" />
              <Text style={s.detailLabel}>Cloudz Earned</Text>
              <Text style={[s.detailValue, { color: '#fbbf24' }]}>+{order.loyaltyPointsEarned}</Text>
            </View>
          )}
        </View>

        <View style={s.pickupCard}>
          <Ionicons name="storefront" size={20} color="#2E6BFF" />
          <Text style={s.pickupText}>
            Contact the store to arrange your pickup location. Show order <Text style={{ fontWeight: 'bold', color: '#2E6BFF' }}>#{shortId}</Text> and a valid 21+ ID.
          </Text>
        </View>

        {order.status === 'Pending Payment' && (
          <TouchableOpacity style={s.cancelBtn} onPress={handleCancel} data-testid="cancel-order-btn">
            <Ionicons name="close-circle-outline" size={18} color="#ef4444" />
            <Text style={s.cancelBtnText}>Cancel Order</Text>
          </TouchableOpacity>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0c0c0c' },
  loadingText: { color: '#999', textAlign: 'center', marginTop: 100, fontSize: 16 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 16 },
  title: { fontSize: 20, fontWeight: 'bold', color: '#fff' },
  content: { flex: 1, padding: 16 },
  statusBanner: { padding: 14, borderRadius: 12, alignItems: 'center', marginBottom: 16 },
  statusLabel: { fontSize: 16, fontWeight: '700' },
  card: { backgroundColor: '#151515', borderRadius: 14, padding: 16, marginBottom: 12 },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#fff', marginBottom: 12 },
  itemRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8 },
  itemQty: { fontSize: 14, color: '#2E6BFF', fontWeight: '700', width: 32 },
  itemName: { flex: 1, fontSize: 14, color: '#ccc' },
  itemPrice: { fontSize: 14, color: '#fff', fontWeight: '600' },
  divider: { height: 1, backgroundColor: '#333', marginVertical: 8 },
  totalLabel: { flex: 1, fontSize: 16, fontWeight: '700', color: '#fff' },
  totalValue: { fontSize: 20, fontWeight: '800', color: '#fff' },
  detailRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#1e1e1e' },
  detailLabel: { flex: 1, fontSize: 14, color: '#999' },
  detailValue: { fontSize: 14, color: '#fff', fontWeight: '600', maxWidth: '55%', textAlign: 'right' },
  pickupCard: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, backgroundColor: '#151515', borderRadius: 14, padding: 16, marginTop: 4 },
  pickupText: { flex: 1, fontSize: 13, color: '#aaa', lineHeight: 20 },
  cancelBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 12, paddingVertical: 14, borderRadius: 14, borderWidth: 1, borderColor: '#ef4444' },
  cancelBtnText: { fontSize: 15, fontWeight: '700', color: '#ef4444' },
});
