import { View, Text, StyleSheet, ScrollView, TouchableOpacity, RefreshControl, Modal, Pressable, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useToast } from '../../components/Toast';
import { useAuthStore } from '../../store/authStore';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface OrderItem {
  productId: string;
  name: string;
  price: number;
  quantity: number;
}

interface Order {
  id: string;
  userId: string;
  customerName?: string;
  customerEmail?: string;
  items: OrderItem[];
  total: number;
  pickupTime: string;
  paymentMethod: string;
  status: string;
  createdAt: string;
  adminNotes?: string;
}

interface Product {
  id: string;
  name: string;
  price: number;
  stock: number;
}

const statusOptions = ['Pending Payment', 'Paid', 'Ready for Pickup', 'Completed', 'Cancelled'];

export default function AdminDashboard() {
  const router = useRouter();
  const toast = useToast();
  const token = useAuthStore(state => state.token);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState('all');
  const [statusModalOrder, setStatusModalOrder] = useState<Order | null>(null);
  const [editModalOrder, setEditModalOrder] = useState<Order | null>(null);
  const [editItems, setEditItems] = useState<OrderItem[]>([]);
  const [editTotal, setEditTotal] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [products, setProducts] = useState<Product[]>([]);
  const [showAddProduct, setShowAddProduct] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (token) { loadOrders(); loadProducts(); }
  }, [token]);

  const loadOrders = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/admin/orders`);
      setOrders(response.data);
    } catch (error) {
      toast.show('Failed to load orders', 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadProducts = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/products`);
      setProducts(res.data);
    } catch {}
  };

  const onRefresh = () => { setRefreshing(true); loadOrders(); };

  const updateOrderStatus = async (orderId: string, newStatus: string) => {
    try {
      await axios.patch(`${API_URL}/api/admin/orders/${orderId}/status`, { status: newStatus });
      await loadOrders();
      setStatusModalOrder(null);
      toast.show(`Status updated to ${newStatus}`);
    } catch {
      toast.show('Failed to update order status', 'error');
    }
  };

  const openEditModal = (order: Order) => {
    setEditModalOrder(order);
    setEditItems(order.items.map(i => ({ ...i })));
    setEditTotal(order.total.toFixed(2));
    setEditNotes(order.adminNotes || '');
    setShowAddProduct(false);
  };

  const updateItemQty = (idx: number, delta: number) => {
    setEditItems(prev => prev.map((it, i) => {
      if (i !== idx) return it;
      const newQty = Math.max(1, it.quantity + delta);
      return { ...it, quantity: newQty };
    }));
  };

  const removeItem = (idx: number) => {
    setEditItems(prev => prev.filter((_, i) => i !== idx));
  };

  const addProduct = (product: Product) => {
    const existing = editItems.findIndex(i => i.productId === product.id);
    if (existing >= 0) {
      setEditItems(prev => prev.map((it, i) => i === existing ? { ...it, quantity: it.quantity + 1 } : it));
    } else {
      setEditItems(prev => [...prev, { productId: product.id, name: product.name, price: product.price, quantity: 1 }]);
    }
    setShowAddProduct(false);
  };

  const saveEdit = async () => {
    if (!editModalOrder) return;
    setSaving(true);
    try {
      await axios.patch(`${API_URL}/api/admin/orders/${editModalOrder.id}/edit`, {
        items: editItems,
        total: parseFloat(editTotal),
        adminNotes: editNotes,
      });
      await loadOrders();
      setEditModalOrder(null);
      toast.show('Order updated');
    } catch {
      toast.show('Failed to update order', 'error');
    } finally {
      setSaving(false);
    }
  };

  const filteredOrders = filter === 'all' ? orders : orders.filter(o => o.status === filter);

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

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#0c0c0c' }} edges={['top']}>
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.title}>Admin Orders</Text>
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
                  <View style={{ flex: 1 }}>
                    <Text style={styles.orderId}>#{order.id.slice(-8)}</Text>
                    <Text style={styles.orderDate}>{new Date(order.createdAt).toLocaleString()}</Text>
                  </View>
                  <View style={[styles.statusBadge, { backgroundColor: getStatusColor(order.status) }]}>
                    <Text style={styles.statusText}>{order.status}</Text>
                  </View>
                </View>

                {/* Customer Info */}
                <TouchableOpacity
                  style={styles.customerRow}
                  onPress={() => order.userId && router.push(`/admin/user-profile?userId=${order.userId}`)}
                  data-testid={`order-customer-${order.id}`}
                >
                  <Ionicons name="person-circle" size={18} color="#6366f1" />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.customerName}>{order.customerName || 'Unknown User'}</Text>
                    <Text style={styles.customerEmail}>{order.customerEmail || order.userId}</Text>
                  </View>
                  <Ionicons name="chevron-forward" size={14} color="#555" />
                </TouchableOpacity>

                <View style={styles.orderDetails}>
                  <View style={styles.detailRow}>
                    <Ionicons name="cart" size={16} color="#666" />
                    <Text style={styles.detailLabel}>Items:</Text>
                    <Text style={styles.detailValue}>{order.items.reduce((sum, item) => sum + item.quantity, 0)}</Text>
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
                    <Text key={index} style={styles.itemText}>{item.quantity}x {item.name}</Text>
                  ))}
                </View>

                {order.adminNotes ? (
                  <View style={styles.adminNotesRow}>
                    <Ionicons name="create" size={13} color="#fbbf24" />
                    <Text style={styles.adminNotesText}>{order.adminNotes}</Text>
                  </View>
                ) : null}

                <View style={styles.actionRow}>
                  <TouchableOpacity
                    style={[styles.actionBtn, styles.editBtn]}
                    onPress={() => openEditModal(order)}
                    data-testid={`edit-order-${order.id}`}
                  >
                    <Ionicons name="create-outline" size={15} color="#fbbf24" />
                    <Text style={[styles.actionBtnText, { color: '#fbbf24' }]}>Edit</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.actionBtn, styles.updateButton]}
                    onPress={() => setStatusModalOrder(order)}
                    data-testid={`update-status-${order.id}`}
                  >
                    <Ionicons name="swap-horizontal" size={15} color="#6366f1" />
                    <Text style={styles.updateButtonText}>Status</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))
          )}
        </ScrollView>

        {/* Status Update Modal */}
        <Modal visible={!!statusModalOrder} transparent animationType="fade" onRequestClose={() => setStatusModalOrder(null)}>
          <Pressable style={styles.modalOverlay} onPress={() => setStatusModalOrder(null)}>
            <View style={styles.modalContent}>
              <Text style={styles.modalTitle}>Update Status</Text>
              <Text style={styles.modalSubtitle}>Order #{statusModalOrder?.id.slice(-8)}</Text>
              {statusOptions.map((status) => (
                <TouchableOpacity
                  key={status}
                  style={[styles.modalOption, statusModalOrder?.status === status && styles.modalOptionCurrent]}
                  onPress={() => statusModalOrder && updateOrderStatus(statusModalOrder.id, status)}
                  data-testid={`status-option-${status}`}
                >
                  <View style={[styles.modalDot, { backgroundColor: getStatusColor(status) }]} />
                  <Text style={styles.modalOptionText}>{status}</Text>
                  {statusModalOrder?.status === status && <Text style={styles.modalCurrentLabel}>current</Text>}
                </TouchableOpacity>
              ))}
              <TouchableOpacity style={styles.modalCancel} onPress={() => setStatusModalOrder(null)} data-testid="status-cancel-btn">
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
            </View>
          </Pressable>
        </Modal>

        {/* Edit Order Modal */}
        <Modal visible={!!editModalOrder} transparent animationType="slide" onRequestClose={() => setEditModalOrder(null)}>
          <View style={styles.editModalOverlay}>
            <View style={styles.editModalContent}>
              <View style={styles.editModalHeader}>
                <Text style={styles.modalTitle}>Edit Order #{editModalOrder?.id.slice(-8)}</Text>
                <TouchableOpacity onPress={() => setEditModalOrder(null)}>
                  <Ionicons name="close" size={22} color="#fff" />
                </TouchableOpacity>
              </View>
              <ScrollView style={{ maxHeight: 400 }} showsVerticalScrollIndicator={false}>
                <Text style={styles.editSectionLabel}>Items</Text>
                {editItems.map((item, idx) => (
                  <View key={idx} style={styles.editItemRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.editItemName}>{item.name}</Text>
                      <Text style={styles.editItemPrice}>${item.price.toFixed(2)} each</Text>
                    </View>
                    <View style={styles.qtyControl}>
                      <TouchableOpacity onPress={() => updateItemQty(idx, -1)} style={styles.qtyBtn}>
                        <Ionicons name="remove" size={14} color="#fff" />
                      </TouchableOpacity>
                      <Text style={styles.qtyText}>{item.quantity}</Text>
                      <TouchableOpacity onPress={() => updateItemQty(idx, 1)} style={styles.qtyBtn}>
                        <Ionicons name="add" size={14} color="#fff" />
                      </TouchableOpacity>
                    </View>
                    <TouchableOpacity onPress={() => removeItem(idx)} style={styles.removeItemBtn}>
                      <Ionicons name="trash-outline" size={16} color="#ef4444" />
                    </TouchableOpacity>
                  </View>
                ))}

                <TouchableOpacity style={styles.addItemBtn} onPress={() => setShowAddProduct(p => !p)}>
                  <Ionicons name="add-circle-outline" size={16} color="#6366f1" />
                  <Text style={styles.addItemText}>Add Product</Text>
                </TouchableOpacity>

                {showAddProduct && (
                  <View style={styles.productPicker}>
                    {products.map(p => (
                      <TouchableOpacity key={p.id} style={styles.productPickerItem} onPress={() => addProduct(p)}>
                        <Text style={styles.productPickerName}>{p.name}</Text>
                        <Text style={styles.productPickerPrice}>${p.price.toFixed(2)}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                )}

                <Text style={styles.editSectionLabel}>Total ($)</Text>
                <TextInput
                  style={styles.editInput}
                  value={editTotal}
                  onChangeText={setEditTotal}
                  keyboardType="decimal-pad"
                  placeholder="0.00"
                  placeholderTextColor="#555"
                  data-testid="edit-order-total"
                />

                <Text style={styles.editSectionLabel}>Admin Notes</Text>
                <TextInput
                  style={[styles.editInput, { minHeight: 60, textAlignVertical: 'top' }]}
                  value={editNotes}
                  onChangeText={setEditNotes}
                  placeholder="Internal notes (not shown to customer)"
                  placeholderTextColor="#555"
                  multiline
                  data-testid="edit-order-notes"
                />
              </ScrollView>

              <TouchableOpacity
                style={[styles.saveEditBtn, saving && { opacity: 0.5 }]}
                onPress={saveEdit}
                disabled={saving}
                data-testid="save-edit-btn"
              >
                <Text style={styles.saveEditText}>{saving ? 'Saving...' : 'Save Changes'}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </Modal>
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
    borderRadius: 18,
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
    borderRadius: 18,
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
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#6366f1',
    flex: 1,
  },
  updateButtonText: {
    fontSize: 14,
    color: '#6366f1',
    fontWeight: '600',
  },
  customerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#111',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginBottom: 12,
  },
  customerName: {
    fontSize: 14,
    fontWeight: '700',
    color: '#6366f1',
  },
  customerEmail: {
    fontSize: 11,
    color: '#666',
    marginTop: 1,
  },
  adminNotesRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    backgroundColor: '#1a1500',
    borderRadius: 8,
    padding: 8,
    marginBottom: 10,
  },
  adminNotesText: {
    fontSize: 12,
    color: '#fbbf24',
    flex: 1,
    lineHeight: 17,
  },
  actionRow: {
    flexDirection: 'row',
    gap: 8,
  },
  actionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    padding: 11,
    borderRadius: 12,
    borderWidth: 1,
    flex: 1,
  },
  editBtn: {
    backgroundColor: '#0c0c0c',
    borderColor: '#fbbf24',
  },
  actionBtnText: {
    fontSize: 13,
    fontWeight: '600',
  },
  editModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'flex-end',
  },
  editModalContent: {
    backgroundColor: '#1a1a1a',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    maxHeight: '90%',
  },
  editModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  editSectionLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#999',
    marginBottom: 8,
    marginTop: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  editItemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0c0c0c',
    borderRadius: 10,
    padding: 10,
    marginBottom: 6,
    gap: 8,
  },
  editItemName: {
    fontSize: 13,
    color: '#fff',
    fontWeight: '600',
  },
  editItemPrice: {
    fontSize: 11,
    color: '#666',
    marginTop: 2,
  },
  qtyControl: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#1a1a1a',
    borderRadius: 8,
    padding: 4,
  },
  qtyBtn: {
    width: 26,
    height: 26,
    borderRadius: 6,
    backgroundColor: '#333',
    alignItems: 'center',
    justifyContent: 'center',
  },
  qtyText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#fff',
    minWidth: 20,
    textAlign: 'center',
  },
  removeItemBtn: {
    padding: 6,
  },
  addItemBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 10,
  },
  addItemText: {
    fontSize: 14,
    color: '#6366f1',
    fontWeight: '600',
  },
  productPicker: {
    backgroundColor: '#0c0c0c',
    borderRadius: 10,
    marginBottom: 8,
    maxHeight: 160,
  },
  productPickerItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  productPickerName: {
    fontSize: 13,
    color: '#fff',
  },
  productPickerPrice: {
    fontSize: 13,
    color: '#10b981',
    fontWeight: '600',
  },
  editInput: {
    backgroundColor: '#0c0c0c',
    borderRadius: 10,
    padding: 12,
    color: '#fff',
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#333',
  },
  saveEditBtn: {
    backgroundColor: '#6366f1',
    borderRadius: 14,
    padding: 15,
    alignItems: 'center',
    marginTop: 16,
  },
  saveEditText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 20,
    width: '100%',
    maxWidth: 360,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  modalSubtitle: {
    fontSize: 13,
    color: '#666',
    marginBottom: 16,
  },
  modalOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 12,
    marginBottom: 6,
    backgroundColor: '#0c0c0c',
    gap: 10,
  },
  modalOptionCurrent: {
    borderWidth: 1,
    borderColor: '#6366f1',
  },
  modalDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  modalOptionText: {
    flex: 1,
    fontSize: 15,
    color: '#fff',
    fontWeight: '500',
  },
  modalCurrentLabel: {
    fontSize: 11,
    color: '#6366f1',
    fontWeight: '600',
  },
  modalCancel: {
    padding: 14,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 6,
  },
  modalCancelText: {
    fontSize: 15,
    color: '#999',
    fontWeight: '500',
  },
});
