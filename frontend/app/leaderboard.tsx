import { View, Text, StyleSheet, FlatList, ActivityIndicator, TouchableOpacity } from 'react-native';
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../store/authStore';
import { theme } from '../theme';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface LeaderboardEntry {
  rank: number;
  displayName: string;
  points: number;
  referralCount: number;
  tier: string | null;
  tierColor: string;
  isCurrentUser: boolean;
}

type Tab = 'points' | 'referrals';

export default function Leaderboard() {
  const router = useRouter();
  const { token } = useAuthStore();
  const [tab, setTab] = useState<Tab>('points');
  const [byPoints, setByPoints] = useState<LeaderboardEntry[]>([]);
  const [byReferrals, setByReferrals] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        const res = await axios.get(`${API_URL}/api/leaderboard`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setByPoints(res.data.byPoints);
        setByReferrals(res.data.byReferrals);
      } catch (e) {
        console.error('Failed to load leaderboard:', e);
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  const data = tab === 'points' ? byPoints : byReferrals;

  const getMedal = (rank: number) => {
    if (rank === 1) return { icon: 'trophy', color: '#FFD700' };
    if (rank === 2) return { icon: 'medal', color: '#C0C0C0' };
    if (rank === 3) return { icon: 'medal', color: '#CD7F32' };
    return null;
  };

  const renderItem = ({ item }: { item: LeaderboardEntry }) => {
    const medal = getMedal(item.rank);
    const score = tab === 'points' ? item.points.toLocaleString() : item.referralCount.toLocaleString();

    return (
      <View
        style={[styles.row, item.isCurrentUser && styles.rowHighlight]}
        data-testid={`leaderboard-rank-${item.rank}`}
      >
        <View style={styles.rankCol}>
          {medal ? (
            <Ionicons name={medal.icon as any} size={22} color={medal.color} />
          ) : (
            <Text style={styles.rankText}>{item.rank}</Text>
          )}
        </View>
        <View style={styles.nameCol}>
          <View style={styles.nameRow}>
            <Text style={[styles.nameText, item.isCurrentUser && styles.nameTextHighlight]}>
              {item.displayName}
            </Text>
            {item.isCurrentUser && <Text style={styles.youBadge}>You</Text>}
          </View>
          {item.tier && (
            <View style={styles.tierRow}>
              <View style={[styles.tierDot, { backgroundColor: item.tierColor }]} />
              <Text style={[styles.tierText, { color: item.tierColor }]}>{item.tier}</Text>
            </View>
          )}
        </View>
        <Text style={styles.scoreText} data-testid="leaderboard-score">{score}</Text>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} data-testid="leaderboard-back-btn">
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Leaderboard</Text>
        <View style={{ width: 24 }} />
      </View>

      {/* Tabs */}
      <View style={styles.tabs} data-testid="leaderboard-tabs">
        <TouchableOpacity
          style={[styles.tab, tab === 'points' && styles.tabActive]}
          onPress={() => setTab('points')}
          data-testid="leaderboard-tab-points"
        >
          <Ionicons name="star" size={16} color={tab === 'points' ? '#fff' : '#666'} />
          <Text style={[styles.tabText, tab === 'points' && styles.tabTextActive]}>Points</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, tab === 'referrals' && styles.tabActive]}
          onPress={() => setTab('referrals')}
          data-testid="leaderboard-tab-referrals"
        >
          <Ionicons name="people" size={16} color={tab === 'referrals' ? '#fff' : '#666'} />
          <Text style={[styles.tabText, tab === 'referrals' && styles.tabTextActive]}>Referrals</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color={theme.colors.primary} style={{ marginTop: 40 }} />
      ) : data.length === 0 ? (
        <View style={styles.empty} data-testid="leaderboard-empty">
          <Ionicons name="podium-outline" size={48} color="#444" />
          <Text style={styles.emptyText}>No rankings yet</Text>
        </View>
      ) : (
        <FlatList
          data={data}
          keyExtractor={(item) => `${tab}-${item.rank}`}
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
  tabs: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 12,
    backgroundColor: theme.colors.card,
    borderRadius: 12,
    padding: 4,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 10,
    borderRadius: 10,
  },
  tabActive: {
    backgroundColor: theme.colors.primary,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
  },
  tabTextActive: {
    color: '#fff',
  },
  list: {
    paddingHorizontal: 16,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.card,
    borderRadius: theme.borderRadius.lg,
    padding: 14,
    marginBottom: 6,
    gap: 12,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  rowHighlight: {
    borderColor: theme.colors.primary,
    backgroundColor: 'rgba(46,107,255,0.08)',
  },
  rankCol: {
    width: 32,
    alignItems: 'center',
  },
  rankText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#555',
  },
  nameCol: {
    flex: 1,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  nameText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
  nameTextHighlight: {
    color: theme.colors.primary,
  },
  youBadge: {
    fontSize: 10,
    fontWeight: 'bold',
    color: theme.colors.primary,
    backgroundColor: 'rgba(46,107,255,0.15)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    overflow: 'hidden',
  },
  tierRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 3,
  },
  tierDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  tierText: {
    fontSize: 11,
    fontWeight: '500',
  },
  scoreText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
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
