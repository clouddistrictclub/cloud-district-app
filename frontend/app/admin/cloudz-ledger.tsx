import { View, Text, StyleSheet, FlatList, ActivityIndicator, TextInput, TouchableOpacity, Platform } from 'react-native';
import { useState, useEffect, useCallback } from 'react';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../../store/authStore';
import { theme } from '../../theme';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface LedgerEntry {
  userId: string;
  userEmail: string;
  type: string;
  amount: number;
  balanceAfter: number;
  reference: string;
  createdAt: string;
}

const TYPE_LABELS: Record<string, string> = {
  purchase_reward: 'Purchase Reward',
  referral_bonus: 'Referral Bonus',
  tier_redemption: 'Tier Redemption',
  admin_adjustment: 'Admin Adjustment',
};

const TYPE_FILTERS = ['all', 'purchase_reward', 'referral_bonus', 'tier_redemption', 'admin_adjustment'];

export default function AdminCloudzLedger() {
  const { token } = useAuthStore();
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

  const renderItem = ({ item }: { item: LedgerEntry }) => {
    const isPositive = item.amount > 0;
    const date = new Date(item.createdAt);
    return (
      <View style={styles.row} data-testid={`admin-ledger-entry-${item.type}`}>
        <View style={styles.rowLeft}>
          <Text style={styles.rowEmail} numberOfLines={1}>{item.userEmail}</Text>
          <Text style={styles.rowType}>{TYPE_LABELS[item.type] || item.type}</Text>
          <Text style={styles.rowRef} numberOfLines={1}>{item.reference}</Text>
        </View>
        <View style={styles.rowRight}>
          <Text style={[styles.rowAmount, { color: isPositive ? '#22c55e' : '#ef4444' }]} data-testid="admin-ledger-amount">
            {isPositive ? '+' : ''}{item.amount.toLocaleString()}
          </Text>
          <Text style={styles.rowBalance}>Bal: {item.balanceAfter.toLocaleString()}</Text>
          <Text style={styles.rowDate}>
            {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} {date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
          </Text>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <Text style={styles.title} data-testid="admin-ledger-title">Cloudz Ledger</Text>
      <Text style={styles.subtitle}>{total.toLocaleString()} total transactions</Text>

      {/* Type filter chips */}
      <View style={styles.filterRow}>
        {TYPE_FILTERS.map((t) => (
          <TouchableOpacity
            key={t}
            style={[styles.chip, typeFilter === t && styles.chipActive]}
            onPress={() => { setTypeFilter(t); setPage(0); }}
            data-testid={`filter-chip-${t}`}
          >
            <Text style={[styles.chipText, typeFilter === t && styles.chipTextActive]}>
              {t === 'all' ? 'All' : (TYPE_LABELS[t] || t)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

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
    </SafeAreaView>
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
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 12,
    gap: 6,
    marginBottom: 8,
  },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: theme.colors.card,
    borderWidth: 1,
    borderColor: '#333',
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
    backgroundColor: theme.colors.card,
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 10,
    padding: 10,
    color: '#fff',
    fontSize: 13,
  },
  filterBtn: {
    backgroundColor: theme.colors.primary,
    borderRadius: 10,
    padding: 10,
  },
  clearBtn: {
    backgroundColor: '#333',
    borderRadius: 10,
    padding: 10,
  },
  list: {
    paddingHorizontal: 12,
  },
  row: {
    flexDirection: 'row',
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.md,
    padding: 12,
    marginBottom: 6,
    gap: 10,
  },
  rowLeft: {
    flex: 1,
  },
  rowEmail: {
    fontSize: 13,
    fontWeight: '600',
    color: '#fff',
  },
  rowType: {
    fontSize: 11,
    color: theme.colors.primary,
    fontWeight: '500',
    marginTop: 2,
  },
  rowRef: {
    fontSize: 11,
    color: '#555',
    marginTop: 2,
  },
  rowRight: {
    alignItems: 'flex-end',
  },
  rowAmount: {
    fontSize: 15,
    fontWeight: 'bold',
  },
  rowBalance: {
    fontSize: 11,
    color: '#555',
    marginTop: 2,
  },
  rowDate: {
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
    backgroundColor: theme.colors.card,
    borderRadius: 8,
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
