import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  TextInput,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../../store/authStore';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

type FilterPreset = 'today' | 'month' | 'custom' | 'all';

interface Analytics {
  totalOrders: number;
  totalRevenue: number;
  avgOrderValue: number;
  avgCLV: number;
  repeatRate: number;
  totalCustomers: number;
  repeatCustomers: number;
  revenueByPayment: { method: string; total: number; count: number }[];
  topProducts: { productId: string; name: string; quantity: number; revenue: number }[];
  topCustomers: { userId: string; name: string; email: string; totalSpent: number; orderCount: number }[];
  lowInventory: { productId: string; name: string; stock: number }[];
  revenueTrendLast7Days?: { date: string; revenue: number }[];
}

const fmt = (n: number) =>
  n >= 1000 ? `$${(n / 1000).toFixed(1)}k` : `$${n.toFixed(2)}`;

const toISO = (d: Date) => d.toISOString().split('T')[0];

export default function AdminDashboard() {
  const router = useRouter();
  const token = useAuthStore(state => state.token);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [preset, setPreset] = useState<FilterPreset>('today');
  const [customStart, setCustomStart] = useState(() => toISO(new Date()));
  const [customEnd, setCustomEnd] = useState(() => toISO(new Date()));

  const getDateRange = useCallback((p: FilterPreset) => {
    const now = new Date();
    const today = toISO(now);
    if (p === 'today') return { startDate: today, endDate: today };
    if (p === 'month') {
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      return { startDate: toISO(start), endDate: today };
    }
    if (p === 'all') return { startDate: '2020-01-01', endDate: today };
    return { startDate: customStart, endDate: customEnd };
  }, [customStart, customEnd]);

  const load = useCallback(async (p: FilterPreset) => {
    if (!token) return;
    setLoading(true);
    try {
      const { startDate, endDate } = getDateRange(p);
      const res = await axios.get(`${API_URL}/api/admin/analytics`, {
        params: { startDate, endDate },
      });
      setAnalytics(res.data);
    } catch (e) {
      console.error('Failed to load analytics', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token, getDateRange]);

  useEffect(() => { load(preset); }, [token]);

  const applyPreset = (p: FilterPreset) => {
    setPreset(p);
    if (p !== 'custom') load(p);
  };

  const applyCustom = () => load('custom');

  const onRefresh = () => { setRefreshing(true); load(preset); };

  const maxPayment = analytics?.revenueByPayment[0]?.total || 1;
  const maxQty = analytics?.topProducts[0]?.quantity || 1;

  const PRESETS: { key: FilterPreset; label: string }[] = [
    { key: 'today', label: 'Today' },
    { key: 'month', label: 'This Month' },
    { key: 'custom', label: 'Custom' },
    { key: 'all', label: 'All Time' },
  ];

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.container}>

        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Analytics</Text>
          <TouchableOpacity onPress={onRefresh}>
            <Ionicons name="refresh" size={22} color={refreshing ? '#6366f1' : '#fff'} />
          </TouchableOpacity>
        </View>

        {/* Filter Row */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterRow} contentContainerStyle={{ gap: 8, paddingHorizontal: 16 }}>
          {PRESETS.map(({ key, label }) => (
            <TouchableOpacity
              key={key}
              style={[styles.filterChip, preset === key && styles.filterChipActive]}
              onPress={() => applyPreset(key)}
              data-testid={`filter-${key}`}
            >
              <Text style={[styles.filterText, preset === key && styles.filterTextActive]}>{label}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Custom Date Picker */}
        {preset === 'custom' && (
          <View style={styles.customPicker}>
            <View style={styles.dateRow}>
              <View style={styles.dateField}>
                <Text style={styles.dateLabel}>From</Text>
                {Platform.OS === 'web' ? (
                  <input
                    type="date"
                    value={customStart}
                    onChange={e => setCustomStart(e.target.value)}
                    style={{ background: '#111', color: '#fff', border: '1px solid #333', borderRadius: 8, padding: '8px 12px', fontSize: 14 }}
                  />
                ) : (
                  <TextInput style={styles.dateInput} value={customStart} onChangeText={setCustomStart} placeholder="YYYY-MM-DD" placeholderTextColor="#555" />
                )}
              </View>
              <View style={styles.dateField}>
                <Text style={styles.dateLabel}>To</Text>
                {Platform.OS === 'web' ? (
                  <input
                    type="date"
                    value={customEnd}
                    onChange={e => setCustomEnd(e.target.value)}
                    style={{ background: '#111', color: '#fff', border: '1px solid #333', borderRadius: 8, padding: '8px 12px', fontSize: 14 }}
                  />
                ) : (
                  <TextInput style={styles.dateInput} value={customEnd} onChangeText={setCustomEnd} placeholder="YYYY-MM-DD" placeholderTextColor="#555" />
                )}
              </View>
            </View>
            <TouchableOpacity style={styles.applyBtn} onPress={applyCustom} data-testid="apply-custom-filter">
              <Text style={styles.applyBtnText}>Apply</Text>
            </TouchableOpacity>
          </View>
        )}

        <ScrollView
          style={styles.scroll}
          showsVerticalScrollIndicator={false}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#6366f1" />}
        >
          {loading ? (
            <View style={styles.loadingBox}>
              <Text style={styles.loadingText}>Loading analytics...</Text>
            </View>
          ) : !analytics ? (
            <View style={styles.loadingBox}>
              <Text style={styles.loadingText}>No data available</Text>
            </View>
          ) : (
            <>
              {/* KPI Cards Row 1 */}
              <View style={styles.cardRow}>
                <StatCard label="Total Orders" value={analytics.totalOrders.toString()} icon="receipt" color="#6366f1" />
                <StatCard label="Revenue" value={fmt(analytics.totalRevenue)} icon="cash" color="#10b981" />
              </View>
              <View style={styles.cardRow}>
                <StatCard label="Avg Order" value={`$${analytics.avgOrderValue.toFixed(2)}`} icon="trending-up" color="#3b82f6" />
                <StatCard label="Avg CLV" value={fmt(analytics.avgCLV)} icon="people" color="#f59e0b" />
              </View>
              <View style={styles.cardRow}>
                <StatCard label="Customers" value={analytics.totalCustomers.toString()} icon="person" color="#8b5cf6" />
                <StatCard
                  label="Repeat Rate"
                  value={`${analytics.repeatRate.toFixed(1)}%`}
                  sub={`${analytics.repeatCustomers} of ${analytics.totalCustomers}`}
                  icon="refresh-circle"
                  color="#ec4899"
                />
              </View>

          {analytics.revenueTrendLast7Days?.length > 0 && (
              <Section title="Revenue Trend (Last 7 Days)" icon="analytics" iconColor="#3b82f6">
                <RevenueTrend data={analytics.revenueTrendLast7Days} />
              </Section>
            )}

              {/* Low Inventory Alert */}
              {analytics.lowInventory.length > 0 && (
                <Section title="Low Inventory Alert" icon="warning" iconColor="#ef4444">
                  {analytics.lowInventory.map((p) => (
                    <View key={p.productId} style={styles.alertRow}>
                      <View style={[styles.stockBadge, p.stock === 0 && styles.stockBadgeOut]}>
                        <Text style={styles.stockBadgeText}>{p.stock === 0 ? 'OUT' : p.stock}</Text>
                      </View>
                      <Text style={styles.alertName} numberOfLines={1}>{p.name}</Text>
                    </View>
                  ))}
                </Section>
              )}

              {/* Revenue by Payment Method */}
              {analytics.revenueByPayment.length > 0 && (
                <Section title="Revenue by Payment Method" icon="card" iconColor="#6366f1">
                  {analytics.revenueByPayment.map((p) => (
                    <View key={p.method} style={styles.barRow}>
                      <View style={{ flex: 1, minWidth: 0 }}>
                        <View style={styles.barLabelRow}>
                          <Text style={styles.barLabel} numberOfLines={1}>{p.method}</Text>
                          <Text style={styles.barValue}>{fmt(p.total)}</Text>
                        </View>
                        <View style={styles.barTrack}>
                          <View style={[styles.barFill, { width: `${(p.total / maxPayment) * 100}%` as any }]} />
                        </View>
                      </View>
                      <Text style={styles.barCount}>{p.count} orders</Text>
                    </View>
                  ))}
                </Section>
              )}

              {/* Top Products */}
              {analytics.topProducts.length > 0 && (
                <Section title="Top Selling Products" icon="cube" iconColor="#10b981">
                  {analytics.topProducts.map((p, i) => (
                    <View key={p.productId} style={styles.rankRow}>
                      <Text style={styles.rankNum}>{i + 1}</Text>
                      <View style={{ flex: 1, minWidth: 0 }}>
                        <Text style={styles.rankName} numberOfLines={1}>{p.name}</Text>
                        <View style={styles.barTrack}>
                          <View style={[styles.barFill, { width: `${(p.quantity / maxQty) * 100}%` as any, backgroundColor: '#10b981' }]} />
                        </View>
                      </View>
                      <View style={styles.rankMeta}>
                        <Text style={styles.rankValue}>{p.quantity} units</Text>
                        <Text style={styles.rankSub}>{fmt(p.revenue)}</Text>
                      </View>
                    </View>
                  ))}
                </Section>
              )}

              {/* Top Customers */}
              {analytics.topCustomers.length > 0 && (
                <Section title="Top Customers" icon="trophy" iconColor="#f59e0b">
                  {analytics.topCustomers.map((c, i) => (
                    <TouchableOpacity
                      key={c.userId}
                      style={styles.rankRow}
                      onPress={() => router.push(`/admin/user-profile?userId=${c.userId}`)}
                      data-testid={`top-customer-${c.userId}`}
                    >
                      <Text style={styles.rankNum}>{i + 1}</Text>
                      <View style={{ flex: 1, minWidth: 0 }}>
                        <Text style={styles.rankName} numberOfLines={1}>{c.name || c.email}</Text>
                        <Text style={styles.rankSub}>{c.orderCount} orders</Text>
                      </View>
                      <View style={styles.rankMeta}>
                        <Text style={[styles.rankValue, { color: '#10b981' }]}>{fmt(c.totalSpent)}</Text>
                        <Ionicons name="chevron-forward" size={13} color="#444" />
                      </View>
                    </TouchableOpacity>
                  ))}
                </Section>
              )}

              <View style={{ height: 32 }} />
            </>
          )}
        </ScrollView>
      </View>
    </SafeAreaView>
  );
}

function StatCard({ label, value, sub, icon, color }: { label: string; value: string; sub?: string; icon: string; color: string }) {
  return (
    <View style={[styles.statCard, { borderLeftColor: color }]}>
      <View style={[styles.statIcon, { backgroundColor: color + '22' }]}>
        <Ionicons name={icon as any} size={18} color={color} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.statLabel}>{label}</Text>
        <Text style={styles.statValue}>{value}</Text>
        {sub ? <Text style={styles.statSub}>{sub}</Text> : null}
      </View>
    </View>
  );
}

function Section({ title, icon, iconColor, children }: { title: string; icon: string; iconColor: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Ionicons name={icon as any} size={16} color={iconColor} />
        <Text style={styles.sectionTitle}>{title}</Text>
      </View>
      {children}
    </View>
  );
}

function RevenueTrend({ data }: { data: { date: string; revenue: number }[] }) {
  const max = Math.max(...data.map(d => d.revenue), 1);
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  return (
    <View style={trendStyles.container}>
      {data.map((d) => {
        const pct = (d.revenue / max) * 100;
        const dayLabel = days[new Date(d.date + 'T12:00:00').getDay()];
        return (
          <View key={d.date} style={trendStyles.col}>
            <Text style={trendStyles.val}>{d.revenue > 0 ? `$${Math.round(d.revenue)}` : ''}</Text>
            <View style={trendStyles.barTrack}>
              <View style={[trendStyles.bar, { height: `${Math.max(pct, 4)}%` as any }]} />
            </View>
            <Text style={trendStyles.day}>{dayLabel}</Text>
          </View>
        );
      })}
    </View>
  );
}

const trendStyles = StyleSheet.create({
  container: { flexDirection: 'row', alignItems: 'flex-end', gap: 6, height: 90 },
  col: { flex: 1, alignItems: 'center', height: '100%' as any, justifyContent: 'flex-end' },
  barTrack: { width: '100%', height: 60, justifyContent: 'flex-end' },
  bar: { width: '100%', backgroundColor: '#3b82f6', borderRadius: 4 },
  val: { fontSize: 8, color: '#3b82f6', marginBottom: 2, textAlign: 'center' },
  day: { fontSize: 10, color: '#666', marginTop: 4, textAlign: 'center' },
});

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0c0c0c' },
  container: { flex: 1, backgroundColor: '#0c0c0c' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  headerTitle: { fontSize: 20, fontWeight: '800', color: '#fff' },
  filterRow: { flexGrow: 0, paddingBottom: 12 },
  filterChip: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 20,
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#2a2a2a',
  },
  filterChipActive: { backgroundColor: '#6366f1', borderColor: '#6366f1' },
  filterText: { fontSize: 13, fontWeight: '600', color: '#777' },
  filterTextActive: { color: '#fff' },
  customPicker: {
    marginHorizontal: 16,
    marginBottom: 12,
    backgroundColor: '#1a1a1a',
    borderRadius: 14,
    padding: 14,
  },
  dateRow: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  dateField: { flex: 1 },
  dateLabel: { fontSize: 11, color: '#666', marginBottom: 6, fontWeight: '600', textTransform: 'uppercase' },
  dateInput: {
    backgroundColor: '#0c0c0c',
    borderRadius: 8,
    padding: 10,
    color: '#fff',
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#333',
  },
  applyBtn: {
    backgroundColor: '#6366f1',
    borderRadius: 10,
    paddingVertical: 11,
    alignItems: 'center',
  },
  applyBtnText: { color: '#fff', fontSize: 14, fontWeight: '700' },
  scroll: { flex: 1 },
  loadingBox: { flex: 1, alignItems: 'center', paddingTop: 80 },
  loadingText: { color: '#555', fontSize: 15 },
  cardRow: { flexDirection: 'row', gap: 10, marginHorizontal: 16, marginBottom: 10 },
  statCard: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: '#1a1a1a',
    borderRadius: 14,
    padding: 14,
    borderLeftWidth: 3,
  },
  statIcon: {
    width: 38,
    height: 38,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  statLabel: { fontSize: 11, color: '#666', fontWeight: '600', textTransform: 'uppercase', marginBottom: 2 },
  statValue: { fontSize: 18, fontWeight: '800', color: '#fff' },
  statSub: { fontSize: 11, color: '#555', marginTop: 1 },
  section: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 14,
  },
  sectionTitle: { fontSize: 14, fontWeight: '700', color: '#fff' },
  alertRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 7,
    borderBottomWidth: 1,
    borderBottomColor: '#222',
  },
  stockBadge: {
    minWidth: 36,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
    backgroundColor: '#fbbf2420',
    alignItems: 'center',
  },
  stockBadgeOut: { backgroundColor: '#ef444420' },
  stockBadgeText: { fontSize: 12, fontWeight: '800', color: '#ef4444' },
  alertName: { fontSize: 13, color: '#ccc', flex: 1 },
  barRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 10,
  },
  barLabelRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  barLabel: { fontSize: 12, color: '#ccc', flex: 1 },
  barValue: { fontSize: 12, fontWeight: '700', color: '#fff' },
  barTrack: { height: 6, backgroundColor: '#2a2a2a', borderRadius: 3, overflow: 'hidden' },
  barFill: { height: 6, backgroundColor: '#6366f1', borderRadius: 3 },
  barCount: { fontSize: 11, color: '#555', minWidth: 55, textAlign: 'right' },
  rankRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 9,
    borderBottomWidth: 1,
    borderBottomColor: '#222',
  },
  rankNum: {
    fontSize: 13,
    fontWeight: '800',
    color: '#555',
    width: 18,
    textAlign: 'center',
  },
  rankName: { fontSize: 13, fontWeight: '600', color: '#fff', marginBottom: 2 },
  rankSub: { fontSize: 11, color: '#555' },
  rankMeta: { alignItems: 'flex-end', gap: 2 },
  rankValue: { fontSize: 13, fontWeight: '700', color: '#fff' },
});
