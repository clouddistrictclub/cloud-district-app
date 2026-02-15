import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { TouchableOpacity } from 'react-native';
import { useAuthStore } from '../store/authStore';
import { theme } from '../theme';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface LedgerEntry {
  userId: string;
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

const TYPE_ICONS: Record<string, string> = {
  purchase_reward: 'cart',
  referral_bonus: 'people',
  tier_redemption: 'diamond',
  admin_adjustment: 'shield',
};

export default function CloudzHistory() {
  const router = useRouter();
  const { token } = useAuthStore();
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await axios.get(`${API_URL}/api/loyalty/ledger`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setEntries(res.data);
      } catch (e) {
        console.error('Failed to load ledger:', e);
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  const renderItem = ({ item }: { item: LedgerEntry }) => {
    const isPositive = item.amount > 0;
    const icon = TYPE_ICONS[item.type] || 'ellipse';
    const label = TYPE_LABELS[item.type] || item.type;
    const date = new Date(item.createdAt);

    return (
      <View style={styles.row} data-testid={`ledger-entry-${item.type}`}>
        <View style={[styles.iconCircle, { backgroundColor: isPositive ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)' }]}>
          <Ionicons name={icon as any} size={18} color={isPositive ? '#22c55e' : '#ef4444'} />
        </View>
        <View style={styles.rowContent}>
          <Text style={styles.rowLabel}>{label}</Text>
          <Text style={styles.rowRef} numberOfLines={1}>{item.reference}</Text>
          <Text style={styles.rowDate}>
            {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} · {date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
          </Text>
        </View>
        <View style={styles.rowRight}>
          <Text style={[styles.rowAmount, { color: isPositive ? '#22c55e' : '#ef4444' }]} data-testid="ledger-amount">
            {isPositive ? '+' : ''}{item.amount.toLocaleString()}
          </Text>
          <Text style={styles.rowBalance}>Bal: {item.balanceAfter.toLocaleString()}</Text>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} data-testid="back-btn">
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Cloudz History</Text>
        <View style={{ width: 24 }} />
      </View>

      {loading ? (
        <ActivityIndicator size="large" color={theme.colors.primary} style={{ marginTop: 40 }} />
      ) : entries.length === 0 ? (
        <View style={styles.empty} data-testid="empty-ledger">
          <Ionicons name="receipt-outline" size={48} color="#444" />
          <Text style={styles.emptyText}>No transactions yet</Text>
          <Text style={styles.emptySubtext}>Your Cloudz activity will appear here</Text>
        </View>
      ) : (
        <FlatList
          data={entries}
          keyExtractor={(_, i) => i.toString()}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
        />
      )}
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
    paddingTop: 8,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  list: {
    padding: 16,
    paddingTop: 0,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.lg,
    padding: 14,
    marginBottom: 8,
    gap: 12,
  },
  iconCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rowContent: {
    flex: 1,
  },
  rowLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  rowRef: {
    fontSize: 12,
    color: theme.colors.textMuted,
    marginTop: 2,
  },
  rowDate: {
    fontSize: 11,
    color: '#555',
    marginTop: 2,
  },
  rowRight: {
    alignItems: 'flex-end',
  },
  rowAmount: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  rowBalance: {
    fontSize: 11,
    color: '#555',
    marginTop: 2,
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  emptyText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
  },
  emptySubtext: {
    fontSize: 13,
    color: '#444',
  },
});
