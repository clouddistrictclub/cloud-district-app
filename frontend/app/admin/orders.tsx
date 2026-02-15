import { View, Text, StyleSheet, ScrollView, TouchableOpacity, RefreshControl, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Order {
  id: string;
  userId: string;
  items: any[];
  total: number;
  pickupTime: string;
  paymentMethod: string;
  status: string;
  createdAt: string;
}

const statusOptions = ['Pending Payment', 'Paid', 'Ready for Pickup', 'Completed'];

export default function AdminDashboard() {
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    loadOrders();
  }, []);

  const loadOrders = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/admin/orders`);
      setOrders(response.data);
    } catch (error) {
      console.error('Failed to load orders:', error);
      Alert.alert('Error', 'Failed to load orders');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadOrders();
  };

  const updateOrderStatus = async (orderId: string, newStatus: string) => {
    try {
      await axios.patch(`${API_URL}/api/admin/orders/${orderId}/status`, {
        status: newStatus
      });
      await loadOrders();
      Alert.alert('Success', `Order status updated to ${newStatus}`);
    } catch (error) {
      console.error('Failed to update order:', error);
      Alert.alert('Error', 'Failed to update order status');
    }
  };

  const showStatusOptions = (order: Order) => {
    const buttons = statusOptions.map(status => ({
      text: status,
      onPress: () => updateOrderStatus(order.id, status)
    }));
    buttons.push({ text: 'Cancel', onPress: () => {}, style: 'cancel' } as any);

    Alert.alert('Update Order Status', `Order #${order.id.slice(-8)}`, buttons);
  };

  const filteredOrders = filter === 'all' 
    ? orders 
    : orders.filter(o => o.status === filter);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Pending Payment': return '#fbbf24';
      case 'Paid': return '#3b82f6';
      case 'Ready for Pickup': return '#10b981';
      case 'Completed': return '#6b7280';
      default: return '#999';
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#0c0c0c' }} edges={['top']}>
      <View style={styles.container}>
        <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Admin Dashboard</Text>
        <TouchableOpacity onPress={onRefresh}>
          <Ionicons name="refresh" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      <View style={styles.filterContainer}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <TouchableOpacity
            style={[styles.filterChip, filter === 'all' && styles.filterChipActive]}
            onPress={() => setFilter('all')}
          >
            <Text style={[styles.filterText, filter === 'all' && styles.filterTextActive]}>
              All ({orders.length})
            </Text>
          </TouchableOpacity>
          {statusOptions.map((status) => {
            const count = orders.filter(o => o.status === status).length;
            return (
              <TouchableOpacity
                key={status}
                style={[styles.filterChip, filter === status && styles.filterChipActive]}
                onPress={() => setFilter(status)}
              >
                <Text style={[styles.filterText, filter === status && styles.filterTextActive]}>
                  {status} ({count})
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>

      <ScrollView 
        style={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#6366f1" />}
      >
        {loading ? (
          <Text style={styles.emptyText}>Loading orders...</Text>
        ) : filteredOrders.length === 0 ? (
          <Text style={styles.emptyText}>No orders found</Text>
        ) : (
          filteredOrders.map((order) => (
            <View key={order.id} style={styles.orderCard}>
              <View style={styles.orderHeader}>
                <View>
                  <Text style={styles.orderId}>#{order.id.slice(-8)}</Text>
                  <Text style={styles.orderDate}>
                    {new Date(order.createdAt).toLocaleString()}
                  </Text>
                </View>
                <View style={[styles.statusBadge, { backgroundColor: getStatusColor(order.status) }]}>
                  <Text style={styles.statusText}>{order.status}</Text>
                </View>
              </View>

              <View style={styles.orderDetails}>
                <View style={styles.detailRow}>
                  <Ionicons name="cart" size={16} color="#666" />
                  <Text style={styles.detailLabel}>Items:</Text>
                  <Text style={styles.detailValue}>{order.items.length}</Text>
                </View>
                <View style={styles.detailRow}>
                  <Ionicons name="cash" size={16} color="#666" />
                  <Text style={styles.detailLabel}>Total:</Text>
                  <Text style={styles.detailValue}>${order.total.toFixed(2)}</Text>
                </View>
                <View style={styles.detailRow}>
                  <Ionicons name="card" size={16} color="#666" />
                  <Text style={styles.detailLabel}>Payment:</Text>
                  <Text style={styles.detailValue}>{order.paymentMethod}</Text>
                </View>
                <View style={styles.detailRow}>
                  <Ionicons name="time" size={16} color="#666" />
                  <Text style={styles.detailLabel}>Pickup:</Text>
                  <Text style={styles.detailValue}>{order.pickupTime}</Text>
                </View>
              </View>

              <View style={styles.itemsList}>
                {order.items.map((item, index) => (
                  <Text key={index} style={styles.itemText}>
                    {item.quantity}x {item.name}
                  </Text>
                ))}
              </View>

              <TouchableOpacity 
                style={styles.updateButton}
                onPress={() => showStatusOptions(order)}
              >
                <Ionicons name="create" size={16} color="#6366f1" />
                <Text style={styles.updateButtonText}>Update Status</Text>
              </TouchableOpacity>
            </View>
          ))
        )}
      </ScrollView>
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
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  filterContainer: {
    paddingHorizontal: 16,
    marginBottom: 16,
  },
  filterChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#1a1a1a',
    marginRight: 8,
  },
  filterChipActive: {
    backgroundColor: '#6366f1',
  },
  filterText: {
    fontSize: 14,
    color: '#999',
    fontWeight: '500',
  },
  filterTextActive: {
    color: '#fff',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    textAlign: 'center',
    marginTop: 32,
  },
  orderCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  orderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  orderId: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  orderDate: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#000',
  },
  orderDetails: {
    marginBottom: 12,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
    gap: 8,
  },
  detailLabel: {
    fontSize: 14,
    color: '#999',
    flex: 1,
  },
  detailValue: {
    fontSize: 14,
    color: '#fff',
    fontWeight: '600',
  },
  itemsList: {
    marginBottom: 12,
  },
  itemText: {
    fontSize: 13,
    color: '#ccc',
    marginBottom: 4,
  },
  updateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#0c0c0c',
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#6366f1',
  },
  updateButtonText: {
    fontSize: 14,
    color: '#6366f1',
    fontWeight: '600',
  },
});
