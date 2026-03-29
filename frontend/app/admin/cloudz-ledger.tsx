import { View, Text, StyleSheet, FlatList, ActivityIndicator, TextInput, TouchableOpacity, Animated } from 'react-native';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../../store/authStore';
import { formatLedgerType, getLedgerIcon, getLedgerColor, ADMIN_LEDGER_FILTERS } from '../../constants/ledger';
import { theme } from '../../theme';
import axios from 'axios';
import { API_URL } from '../../constants/api';

interface LedgerEntry {
  userId: string;
  userEmail: string;
  type: string;
  amount: number;
  balanceAfter: number;
  reference: string;
  description?: string;
  createdAt: string;
}

function AdminLedgerRow({ item, index }: { item: LedgerEntry; index: number }) {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(12)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 280,
        delay: index * 30,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 280,
        delay: index * 30,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  const color = getLedgerColor(item.type, item.amount);
  const icon = getLedgerIcon(item.type);
  const label = formatLedgerType(item.type);
  const isPositive = item.amount > 0;
  const date = new Date(item.createdAt);
  const subtext = item.description || item.reference || '';

  return (
    <Animated.View
      style={[styles.card, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}
      data-testid={`admin-ledger-entry-${item.type}`}
    >
      <View style={[styles.iconCircle, { backgroundColor: `${color}18` }]}>
        <Ionicons name={icon as any} size={18} color={color} />
      </View>
      <View style={styles.cardContent}>
        <Text style={styles.cardEmail} numberOfLines={1}>{item.userEmail}</Text>
        <Text style={[styles.cardLabel, { color }]}>{label}</Text>
        {subtext ? (
          <Text style={styles.cardSubtext} numberOfLines={1}>{subtext}</Text>
        ) : null}
      </View>
      <View style={styles.cardRight}>
        <Text style={[styles.cardAmount, { color }]} data-testid="admin-ledger-amount">
          {isPositive ? '+' : ''}{(item.amount ?? 0).toLocaleString()}
        </Text>
        <Text style={styles.cardBalance}>Bal: {(item.balanceAfter ?? 0).toLocaleString()}</Text>
        <Text style={styles.cardDate}>
          {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} {date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
        </Text>
      </View>
    </Animated.View>
  );
}

export default function AdminCloudzLedger() {
  const { token } = useAuthStore();
  const insets = useSafeAreaInsets();
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [typeFilter, setTypeFilter] = useState('all');
  const [userIdFilter, setUserIdFilter] = useState('');
  const [appliedUserId, setAppliedUserId] = useState('');
  const PAGE_SIZE = 50;

  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  const loadData = useCallback(async (pageNum: number, type: string, userId: string) => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { skip: pageNum * PAGE_SIZE, limit: PAGE_SIZE };
      if (type !== 'all') params.type = type;
      if (userId.trim()) params.userId = userId.trim();
      const res = await axios.get(`${API_URL}/api/admin/ledger`, { ...authHeaders, params });
      setEntries(res.data.entries);
      setTotal(res.data.total);
    } catch (e) {
      console.error('Failed to load admin ledger:', e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) loadData(page, typeFilter, appliedUserId);
  }, [page, typeFilter, appliedUserId, token]);

  const handleApplyUserId = () => {
    setPage(0);
    setAppliedUserId(userIdFilter);
  };

  const handleClearUserId = () => {
    setUserIdFilter('');
    setAppliedUserId('');
    setPage(0);
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const renderItem = ({ item, index }: { item: LedgerEntry; index: number }) => (
    <AdminLedgerRow item={item} index={index} />
  );

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <Text style={styles.title} data-testid="admin-ledger-title">Cloudz Ledger</Text>
      <Text style={styles.subtitle}>{total.toLocaleString()} total transactions</Text>

      {/* Type filter chips — scrollable row */}
      <FlatList
        horizontal
        data={[...ADMIN_LEDGER_FILTERS]}
        keyExtractor={(t) => t}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filterRow}
        renderItem={({ item: t }) => (
          <TouchableOpacity
            style={[styles.chip, typeFilter === t && styles.chipActive]}
            onPress={() => { setTypeFilter(t); setPage(0); }}
            data-testid={`filter-chip-${t}`}
          >
            <Text style={[styles.chipText, typeFilter === t && styles.chipTextActive]}>
              {t === 'all' ? 'All' : formatLedgerType(t)}
            </Text>
          </TouchableOpacity>
        )}
      />

      {/* User ID filter */}
      <View style={styles.userFilterRow}>
        <TextInput
          style={styles.userFilterInput}
          placeholder="Filter by User ID..."
          placeholderTextColor="#555"
          value={userIdFilter}
          onChangeText={setUserIdFilter}
          onSubmitEditing={handleApplyUserId}
          data-testid="admin-ledger-userid-filter"
        />
        <TouchableOpacity style={styles.filterBtn} onPress={handleApplyUserId} data-testid="admin-ledger-apply-filter">
          <Ionicons name="search" size={18} color="#fff" />
        </TouchableOpacity>
        {appliedUserId ? (
          <TouchableOpacity style={styles.clearBtn} onPress={handleClearUserId} data-testid="admin-ledger-clear-filter">
            <Ionicons name="close" size={18} color="#fff" />
          </TouchableOpacity>
        ) : null}
      </View>

      {loading ? (
        <ActivityIndicator size="large" color={theme.colors.primary} style={{ marginTop: 32 }} />
      ) : entries.length === 0 ? (
        <View style={styles.empty} data-testid="admin-ledger-empty">
          <Ionicons name="receipt-outline" size={48} color="#444" />
          <Text style={styles.emptyText}>No ledger entries found</Text>
        </View>
      ) : (
        <>
          <FlatList
            data={entries}
            keyExtractor={(_, i) => `${page}-${i}`}
            renderItem={renderItem}
            contentContainerStyle={styles.list}
            showsVerticalScrollIndicator={false}
          />
          {/* Pagination */}
          <View style={styles.pagination} data-testid="admin-ledger-pagination">
            <TouchableOpacity
              style={[styles.pageBtn, page === 0 && styles.pageBtnDisabled]}
              onPress={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              data-testid="admin-ledger-prev-page"
            >
              <Ionicons name="chevron-back" size={18} color={page === 0 ? '#444' : '#fff'} />
            </TouchableOpacity>
            <Text style={styles.pageText}>
              Page {page + 1} of {Math.max(1, totalPages)}
            </Text>
            <TouchableOpacity
              style={[styles.pageBtn, page >= totalPages - 1 && styles.pageBtnDisabled]}
              onPress={() => setPage(page + 1)}
              disabled={page >= totalPages - 1}
              data-testid="admin-ledger-next-page"
            >
              <Ionicons name="chevron-forward" size={18} color={page >= totalPages - 1 ? '#444' : '#fff'} />
            </TouchableOpacity>
          </View>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#fff',
    paddingHorizontal: 16,
    paddingTop: 12,
  },
  subtitle: {
    fontSize: 13,
    color: theme.colors.textMuted,
    paddingHorizontal: 16,
    marginBottom: 12,
  },
  filterRow: {
    paddingHorizontal: 12,
    gap: 6,
    marginBottom: 8,
    paddingVertical: 2,
  },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 20,
    backgroundColor: '#1A1A1A',
    borderWidth: 1,
    borderColor: '#2A2A2A',
  },
  chipActive: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primary,
  },
  chipText: {
    fontSize: 12,
    color: theme.colors.textMuted,
    fontWeight: '500',
  },
  chipTextActive: {
    color: '#fff',
    fontWeight: '600',
  },
  userFilterRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    gap: 6,
    marginBottom: 10,
  },
  userFilterInput: {
    flex: 1,
    backgroundColor: '#1A1A1A',
    borderWidth: 1,
    borderColor: '#2A2A2A',
    borderRadius: 12,
    padding: 10,
    color: '#fff',
    fontSize: 13,
  },
  filterBtn: {
    backgroundColor: theme.colors.primary,
    borderRadius: 12,
    padding: 10,
  },
  clearBtn: {
    backgroundColor: '#333',
    borderRadius: 12,
    padding: 10,
  },
  list: {
    paddingHorizontal: 12,
    paddingBottom: 8,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1A1A1A',
    borderRadius: 16,
    padding: 14,
    marginBottom: 10,
    gap: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 3,
  },
  iconCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardContent: {
    flex: 1,
  },
  cardEmail: {
    fontSize: 13,
    fontWeight: '600',
    color: '#fff',
  },
  cardLabel: {
    fontSize: 11,
    fontWeight: '500',
    marginTop: 2,
  },
  cardSubtext: {
    fontSize: 11,
    color: '#555',
    marginTop: 2,
  },
  cardRight: {
    alignItems: 'flex-end',
  },
  cardAmount: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  cardBalance: {
    fontSize: 11,
    color: '#555',
    marginTop: 2,
  },
  cardDate: {
    fontSize: 10,
    color: '#444',
    marginTop: 2,
  },
  pagination: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
    paddingVertical: 12,
  },
  pageBtn: {
    backgroundColor: '#1A1A1A',
    borderRadius: 10,
    padding: 8,
  },
  pageBtnDisabled: {
    opacity: 0.4,
  },
  pageText: {
    fontSize: 13,
    color: theme.colors.textMuted,
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  emptyText: {
    fontSize: 15,
    color: '#666',
    fontWeight: '500',
  },
});
