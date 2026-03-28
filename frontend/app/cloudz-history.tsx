import { View, Text, StyleSheet, FlatList, ActivityIndicator, Animated } from 'react-native';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { TouchableOpacity } from 'react-native';
import { useAuthStore } from '../store/authStore';
import { formatLedgerType, getLedgerIcon, getLedgerColor } from '../constants/ledger';
import { theme } from '../theme';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface LedgerEntry {
  userId: string;
  type: string;
  amount: number;
  balanceAfter: number;
  reference: string;
  description?: string;
  createdAt: string;
}

function LedgerRow({ item, index }: { item: LedgerEntry; index: number }) {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(12)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 300,
        delay: index * 40,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 300,
        delay: index * 40,
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
      data-testid={`ledger-entry-${item.type}`}
    >
      <View style={[styles.iconCircle, { backgroundColor: `${color}18` }]}>
        <Ionicons name={icon as any} size={20} color={color} />
      </View>
      <View style={styles.cardContent}>
        <Text style={styles.cardLabel}>{label}</Text>
        {subtext ? (
          <Text style={styles.cardSubtext} numberOfLines={1}>{subtext}</Text>
        ) : null}
        <Text style={styles.cardDate}>
          {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} · {date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
        </Text>
      </View>
      <View style={styles.cardRight}>
        <Text style={[styles.cardAmount, { color }]} data-testid="ledger-amount">
          {isPositive ? '+' : ''}{(item.amount ?? 0).toLocaleString()}
        </Text>
        <Text style={styles.cardBalance}>Bal: {(item.balanceAfter ?? 0).toLocaleString()}</Text>
      </View>
    </Animated.View>
  );
}

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
        setEntries(Array.isArray(res.data) ? res.data : []);
      } catch (e) {
        console.error('Failed to load ledger:', e);
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  const renderItem = ({ item, index }: { item: LedgerEntry; index: number }) => (
    <LedgerRow item={item} index={index} />
  );

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
    paddingHorizontal: 14,
    paddingTop: 4,
    paddingBottom: 24,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1A1A1A',
    borderRadius: 16,
    padding: 14,
    marginBottom: 10,
    gap: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 3,
  },
  iconCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardContent: {
    flex: 1,
  },
  cardLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  cardSubtext: {
    fontSize: 12,
    color: '#777',
    marginTop: 2,
  },
  cardDate: {
    fontSize: 11,
    color: '#555',
    marginTop: 3,
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
    marginTop: 3,
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
